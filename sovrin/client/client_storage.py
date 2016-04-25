import os
from collections import OrderedDict

import pyorient

from ledger.immutable_store.serializers.compact_serializer import \
    CompactSerializer
from ledger.immutable_store.stores import TextFileStore
from plenum.persistence.orientdb_store import OrientDbStore
from plenum.common.has_file_storage import HasFileStorage
from sovrin.common.txn import getTxnOrderedFields
from sovrin.common.util import getConfig
from sovrin.persistence.client_document_store import ClientDocumentStore


# TODO Client storage should be a mixin of document storage and graph storage


class ClientStorage(HasFileStorage, ClientDocumentStore):

    def __init__(self, clientName, baseDirPath=None):
        self.dataDir = "data/clients"
        self.name = clientName
        HasFileStorage.__init__(self, clientName,
                                baseDir=baseDirPath,
                                dataDir=self.dataDir)
        self.clientDataLocation = self.getDataLocation()
        if not os.path.exists(self.clientDataLocation):
            os.makedirs(self.clientDataLocation)
        self.serializer = CompactSerializer()
        self.txnFields = getTxnOrderedFields()
        self.transactionLog = TextFileStore(self.clientDataLocation, "transactions")
        config = getConfig()
        ClientDocumentStore.__init__(self, OrientDbStore(user=config.OrientDB["user"],
                                     password=config.OrientDB["password"],
                                     dbName=clientName,
                                     storageType=pyorient.STORAGE_TYPE_PLOCAL))

    def _serializeTxn(self, res):
        return self.serializer.serialize(res,
                                         fields=self.txnFields,
                                         toBytes=False)

    def addToTransactionLog(self, reqId, txn):
        self.transactionLog.put(str(reqId), self._serializeTxn(txn))
