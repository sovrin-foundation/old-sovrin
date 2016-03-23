from ledger.immutable_store.ledger import Ledger

from ledger.immutable_store.merkle import CompactMerkleTree
from sovrin.persistence.chain_store import ChainStore


class LedgerChainStore(Ledger, ChainStore):
    def __init__(self, dataLocation):
        Ledger.__init__(self, CompactMerkleTree(), dataLocation)