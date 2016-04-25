import base64
from collections import OrderedDict

import pyorient

from ledger.immutable_store.ledger import Ledger

from ledger.immutable_store.merkle import CompactMerkleTree
from ledger.immutable_store.serializers.compact_serializer import \
    CompactSerializer
from plenum.common.types import f

from plenum.persistence.orientdb_store import OrientDbStore
from sovrin.common.txn import TXN_ID, TXN_TYPE, ORIGIN, TARGET_NYM, DATA, ROLE, \
    REFERENCE, getTxnOrderedFields
from sovrin.common.txn import TXN_TIME
from sovrin.persistence.chain_store import ChainStore
from sovrin.common.util import getConfig
from sovrin.persistence.node_document_store import NodeDocumentStore


class LedgerChainStore(Ledger, ChainStore, NodeDocumentStore):
    def __init__(self, name, dataLocation, config):
        # def b64e(s):
        #     return base64.b64encode(s).decode("utf-8")
        #
        # def b64d(s):
        #     return base64.b64decode(s)
        #
        # def lst2str(l):
        #     return ",".join(l)

        orderedFields = getTxnOrderedFields()

        Ledger.__init__(self, CompactMerkleTree(), dataDir=dataLocation,
                        serializer=CompactSerializer(orderedFields))

        NodeDocumentStore.__init__(self, OrientDbStore(
            user=config.OrientDB["user"],
            password=config.OrientDB["password"],
            dbName=name,
            storageType=pyorient.STORAGE_TYPE_PLOCAL))
