import base64
from collections import OrderedDict

import pyorient

from ledger.immutable_store.ledger import Ledger

from ledger.immutable_store.merkle import CompactMerkleTree
from ledger.immutable_store.serializers.compact_serializer import \
    CompactSerializer
from sovrin.common.txn import TXN_ID, TXN_TYPE, ORIGIN, TARGET_NYM, DATA, ROLE, \
    REFERENCE
from sovrin.common.txn import TXN_TIME
from sovrin.persistence.chain_store import ChainStore
from sovrin.common.util import getConfig
from sovrin.persistence.node_document_store import NodeDocumentStore


class LedgerChainStore(Ledger, ChainStore, NodeDocumentStore):
    def __init__(self, name, dataLocation):
        # def b64e(s):
        #     return base64.b64encode(s).decode("utf-8")
        #
        # def b64d(s):
        #     return base64.b64decode(s)
        #
        # def lst2str(l):
        #     return ",".join(l)

        orderedFields = OrderedDict([
            (TXN_ID, (str, str)),
            (TXN_TIME, (str, float)),
            (TXN_TYPE, (str, str)),
            (ORIGIN, (str, str)),
            (TARGET_NYM, (str, str)),
            (DATA, (str, str)),
            (ROLE, (str, str)),
            (REFERENCE, (str, str))
        ])

        Ledger.__init__(self, CompactMerkleTree(), dataDir=dataLocation,
                        serializer=CompactSerializer(orderedFields))

        config = getConfig()

        NodeDocumentStore.__init__(self, user=config.GraphDB["user"],
                                     password=config.GraphDB["password"],
                                     dbName=name,
                                     storageType=pyorient.STORAGE_TYPE_PLOCAL)