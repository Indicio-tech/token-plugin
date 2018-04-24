import json

import pytest

from ledger.util import F
from plenum.common.constants import TXN_TYPE, CONFIG_LEDGER_ID
from plenum.common.exceptions import RequestRejectedException
from plenum.server.plugin.fees.src.constants import FEES
from plenum.server.plugin.token.src.constants import XFER_PUBLIC
from plenum.server.plugin.token.src.util import update_token_wallet_with_result
from plenum.server.plugin.token.test.helper import send_xfer
from plenum.test.helper import sdk_send_and_check
from plenum.server.plugin.token.test.conftest import seller_gets
from plenum.server.plugin.fees.test.test_set_get_fees import fees_set


def test_xfer_with_insufficient_fees(public_minting, looper, fees_set,
                                     nodeSetWithIntegratedTokenPlugin,
                                     sdk_pool_handle,
                                     seller_token_wallet, seller_address, user1_address,
                                     user1_token_wallet):
    # Payed fees is less than required fees
    global seller_gets
    seq_no = public_minting[F.seqNo.name]
    fee_amount = fees_set[FEES][XFER_PUBLIC]
    user1_gets = 10
    seller_remaining = seller_gets - (user1_gets + fee_amount - 1)
    inputs = [[seller_token_wallet, seller_address, seq_no]]
    outputs = [[user1_address, user1_gets], [seller_address, seller_remaining]]
    with pytest.raises(RequestRejectedException):
        send_xfer(looper, inputs, outputs, sdk_pool_handle)


def test_xfer_with_sufficient_fees(public_minting, looper, fees_set,
                   nodeSetWithIntegratedTokenPlugin, sdk_pool_handle,
                   seller_token_wallet, seller_address, user1_address,
                   user1_token_wallet):
    global seller_gets
    seq_no = public_minting[F.seqNo.name]
    fee_amount = fees_set[FEES][XFER_PUBLIC]
    user1_gets = 10
    seller_remaining = seller_gets - (user1_gets + fee_amount)
    inputs = [[seller_token_wallet, seller_address, seq_no]]
    outputs = [[user1_address, user1_gets], [seller_address, seller_remaining]]
    res = send_xfer(looper, inputs, outputs, sdk_pool_handle)
    update_token_wallet_with_result(seller_token_wallet, res)
    update_token_wallet_with_result(user1_token_wallet, res)
    assert seller_remaining == seller_token_wallet.get_total_address_amount(seller_address)
    assert user1_gets == user1_token_wallet.get_total_address_amount(user1_address)
    seller_gets = seller_remaining
    for node in nodeSetWithIntegratedTokenPlugin:
        req_handler = node.get_req_handler(CONFIG_LEDGER_ID)
        assert req_handler.deducted_fees[res[F.seqNo.name]] == fee_amount