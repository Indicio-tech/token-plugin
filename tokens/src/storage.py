from plenum.common.ledger import Ledger
from ledger.compact_merkle_tree import CompactMerkleTree
from plenum.persistence.leveldb_hash_store import LevelDbHashStore
from plenum.persistence.storage import initKeyValueStorage
from state.pruning_state import PruningState

from tokens.src.utxo_cache import UTXOCache


def get_token_hash_store(data_dir):
    return LevelDbHashStore(dataDir=data_dir,
                            fileNamePrefix='tokens')


def get_token_ledger(data_dir, name, hash_store, config):
    return Ledger(CompactMerkleTree(hashStore=hash_store),
                  dataDir=data_dir,
                  fileName=name,
                  ensureDurability=config.EnsureLedgerDurability)


def get_token_state(data_dir, name, config):
    return PruningState(initKeyValueStorage(
        config.tokenStateStorage, data_dir, name))


def get_utxo_cache(data_dir, name, config):
    return UTXOCache(initKeyValueStorage(
        config.utxoCacheStorage, data_dir, name))