import functools

from sovtokenfees.constants import ACCEPTABLE_WRITE_TYPES_FEE, ACCEPTABLE_QUERY_TYPES_FEE, ACCEPTABLE_ACTION_TYPES_FEE, \
    FEE_TXN
from sovtokenfees.req_handlers.batch_handlers.fee_batch_handler import DomainFeeBatchHandler
from sovtokenfees.req_handlers.batch_handlers.tracker_batch_handler import TrackerBatchHandler
from sovtokenfees.req_handlers.read_handlers.get_fee_handler import GetFeeHandler
from sovtokenfees.req_handlers.read_handlers.get_fees_handler import GetFeesHandler
from sovtokenfees.req_handlers.write_handlers.auth_rule_fee_handler import AuthRuleFeeHandler
from sovtokenfees.req_handlers.write_handlers.fee_txn_handler import FeeTxnCatchupHandler
from sovtokenfees.req_handlers.write_handlers.set_fees_handler import SetFeesHandler
from sovtokenfees.req_handlers.write_handlers.xfer_fee_handler import XferFeeHandler
from sovtokenfees.req_handlers.fees_utils import BatchFeesTracker
from sovtokenfees.req_handlers.write_handlers.domain_fee_handler import DomainFeeHandler

from plenum.common.ledger_uncommitted_tracker import LedgerUncommittedTracker

from sovtoken.constants import UTXO_CACHE_LABEL, XFER_PUBLIC
from sovtokenfees.sovtokenfees_auth_map import sovtokenfees_auth_map

from sovtokenfees.transactions import FeesTransactions
from typing import Any
from sovtokenfees.fees_authorizer import FeesAuthorizer

from plenum.common.constants import DOMAIN_LEDGER_ID, NodeHooks, ReplicaHooks

from indy_common.constants import CONFIG_LEDGER_ID, AUTH_RULES, AUTH_RULE

from plenum.common.txn_util import get_type
from sovtokenfees.client_authnr import FeesAuthNr
from sovtoken import TOKEN_LEDGER_ID
from sovtoken.client_authnr import TokenAuthNr

from sovtokenfees.req_handlers.write_handlers.auth_rules_fee_handler import AuthRulesFeeHandler

from plenum.common.messages.internal_messages import PreSigVerification


def integrate_plugin_in_node(node):
    token_ledger = node.db_manager.get_ledger(TOKEN_LEDGER_ID)
    token_state = node.db_manager.get_state(TOKEN_LEDGER_ID)

    fees_tracker = register_trackers(node, token_state, token_ledger)
    node.write_req_validator.auth_map.update(sovtokenfees_auth_map)
    register_req_handlers(node, fees_tracker)
    register_batch_handlers(node, fees_tracker)
    set_callbacks(node)
    fees_authnr = register_authentication(node)
    register_hooks(node, fees_authnr)
    return node


def register_req_handlers(node, fees_tracker):
    node.write_manager.register_req_handler(SetFeesHandler(node.db_manager,
                                                           node.write_req_validator))

    if XFER_PUBLIC not in node.write_manager.request_handlers:
        raise ImportError('sovtoken plugin should be loaded, request '
                          'handler not found')
    node.write_manager.remove_req_handler(XFER_PUBLIC)
    node.write_manager.register_req_handler(XferFeeHandler(node.db_manager,
                                                           node.write_req_validator))

    domain_fee_r_h = DomainFeeHandler(node.db_manager, fees_tracker)
    for typ in list(node.write_manager.ledger_id_to_types[DOMAIN_LEDGER_ID]):
        node.write_manager.register_req_handler(domain_fee_r_h, typ=typ)

    node.write_manager.register_req_handler(FeeTxnCatchupHandler(node.db_manager))
    node.read_manager.register_req_handler(GetFeeHandler(node.db_manager))
    gfs_handler = GetFeesHandler(node.db_manager)
    node.read_manager.register_req_handler(gfs_handler)

    node.write_manager.register_req_handler(AuthRuleFeeHandler(node.db_manager, gfs_handler))
    node.write_manager.register_req_handler(AuthRulesFeeHandler(node.db_manager, gfs_handler))


def register_batch_handlers(node, fees_tracker):
    domain_fee_batch_handler = DomainFeeBatchHandler(node.db_manager, fees_tracker)
    tracker_batch_handler = TrackerBatchHandler(node.db_manager)
    node.write_manager.register_batch_handler(domain_fee_batch_handler)
    node.write_manager.register_batch_handler(tracker_batch_handler)


def set_callbacks(node):
    set_post_catchup_callback(node)
    set_post_added_txn_callback(node)


def set_post_catchup_callback(node):
    def postCatchupCompleteClbk(node):
        token_tracker = node.db_manager.get_tracker(TOKEN_LEDGER_ID)
        token_state = node.db_manager.get_state(TOKEN_LEDGER_ID)
        token_ledger = node.db_manager.get_ledger(TOKEN_LEDGER_ID)
        token_tracker.set_last_committed(token_state.committedHeadHash,
                                         token_ledger.uncommitted_root_hash,
                                         token_ledger.size)

    origin_token_clb = node.ledgerManager.ledgerRegistry[TOKEN_LEDGER_ID].postCatchupCompleteClbk

    def postCatchupCompleteClb(origin_clb):
        if origin_clb:
            origin_clb()
        postCatchupCompleteClbk(node)

    node.ledgerManager.ledgerRegistry[TOKEN_LEDGER_ID].postCatchupCompleteClbk = \
        functools.partial(postCatchupCompleteClb, origin_token_clb)


def set_post_added_txn_callback(node):
    origin_token_post_added_clb = node.ledgerManager.ledgerRegistry[TOKEN_LEDGER_ID].postTxnAddedToLedgerClbk

    def filter_fees(ledger_id: int, txn: Any):
        origin_token_post_added_clb(ledger_id, txn, get_type(txn) != FeesTransactions.FEES.value)

    node.ledgerManager.ledgerRegistry[TOKEN_LEDGER_ID].postTxnAddedToLedgerClbk = filter_fees


def register_authentication(node):
    utxo_cache = node.db_manager.get_store(UTXO_CACHE_LABEL)
    token_authnr = node.clientAuthNr.get_authnr_by_type(TokenAuthNr)
    if not token_authnr:
        raise ImportError('sovtoken plugin should be loaded, '  # noqa
                          'authenticator not found')
    fees_authnr = FeesAuthNr(ACCEPTABLE_WRITE_TYPES_FEE, ACCEPTABLE_QUERY_TYPES_FEE, ACCEPTABLE_ACTION_TYPES_FEE,
                             node.db_manager.idr_cache, token_authnr)
    node.clientAuthNr.register_authenticator(fees_authnr)
    fees_authorizer = FeesAuthorizer(config_state=node.getState(CONFIG_LEDGER_ID),
                                     utxo_cache=utxo_cache)
    node.write_req_validator.register_authorizer(fees_authorizer)
    return fees_authnr


def register_hooks(node, fees_authnr):
    register_auth_hooks(node, fees_authnr)


def register_auth_hooks(node, fees_authnr):
    node.replicas.subscribe_to_internal_bus(PreSigVerification,
                                            fees_authnr.verify_signature,
                                            node.master_replica.instId)


def register_trackers(node, token_state, token_ledger):
    # TODO: move trackers into write_manager
    fees_tracker = BatchFeesTracker()
    token_tracker = LedgerUncommittedTracker(token_state.committedHeadHash,
                                             token_ledger.uncommitted_root_hash,
                                             token_ledger.size)
    node.db_manager.register_new_tracker(TOKEN_LEDGER_ID, token_tracker)
    return fees_tracker
