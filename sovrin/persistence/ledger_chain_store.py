import base64
from collections import OrderedDict

from ledger.immutable_store.ledger import Ledger

from ledger.immutable_store.merkle import CompactMerkleTree
from ledger.immutable_store.serializers.compact_serializer import \
    CompactSerializer
from sovrin.persistence.chain_store import ChainStore


class LedgerChainStore(Ledger, ChainStore):
    def __init__(self, dataLocation):
        def b64e(s):
            return base64.b64encode(s).decode("utf-8")

        def b64d(s):
            return base64.b64decode(s)

        def lst2str(l):
            return ",".join(l)

        orderedFields = OrderedDict([
            ("serial_no", (str, int)),
            ("STH.tree_size", (str, int)),
            ("STH.root_hash", (b64e, b64d)),
            ("leaf_data.txnId", (str, str)),
            ("leaf_data.txnTime", (str, float)),
            ("leaf_data.type", (str, str)),
            ("leaf_data.origin", (str, str)),
            ("leaf_data.dest", (str, str)),
            ("leaf_data.data", (str, str)),
            ("leaf_data.role", (str, str)),
            ("leaf_data.reference", (str, str)),
            ("leaf_data_hash", (b64e, b64d)),
            ("audit_info", (lst2str, str.split))
        ])

        Ledger.__init__(self, CompactMerkleTree(), dataDir=dataLocation,
                        serializer=CompactSerializer(orderedFields))
