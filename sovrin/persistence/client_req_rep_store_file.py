import json

import os
from collections import OrderedDict

from ledger.util import F
from plenum.common.util import updateFieldsWithSeqNo
from plenum.persistence.client_req_rep_store_file import ClientReqRepStoreFile \
    as PClientReqRepStoreFile

from sovrin.common.txn import getTxnOrderedFields


class ClientReqRepStoreFile(PClientReqRepStoreFile):
    def __init__(self, name, baseDir):
        super().__init__(name, baseDir)
        self.lastTxnsFileName = "last_txn_for_id"

    @property
    def txnFieldOrdering(self):
        fields = getTxnOrderedFields()
        return updateFieldsWithSeqNo(fields)

    def setLastTxnForIdentifier(self, identifier, value: str):
        filePath = os.path.join(self.dataLocation, self.lastTxnsFileName)
        if not os.path.exists(filePath):
            open(filePath, 'w').close()
        with open(filePath, "r+") as f:
            data = f.read().strip()
            data = json.loads(data) if data else {}
            data[identifier] = value
            f.write(json.dumps(data))

    def getLastTxnForIdentifier(self, identifier):
        try:
            with open(os.path.join(self.dataLocation, self.lastTxnsFileName),
                      "r") as f:
                data = f.read().strip()
                data = json.loads(data) if data else {}
                return data.get(identifier)
        except FileNotFoundError:
            return None
