from plenum.common.transaction_store import TransactionStore
from sovrin.persistence.chain_store import ChainStore


class MemoryChainStore(TransactionStore, ChainStore):
    pass
