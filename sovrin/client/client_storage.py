import os
from typing import Any
import pickle

import plyvel

import sovrin


class ClientStorage:
    dataLocation = "data/clients"
    packagePath = sovrin.__file__
    currentPath = os.path.dirname(packagePath)

    def __init__(self, clientName):
        self.clientName = clientName
        self.clientDataLocation = self.__class__.getDataLocation(clientName)
        if not os.path.exists(self.clientDataLocation):
            os.makedirs(self.clientDataLocation)
        self.store = plyvel.DB(self.clientDataLocation, create_if_missing=True)
        self.reqStore = self.store.prefixed_db(b'RQ-')
        self.ackStore = self.store.prefixed_db(b'A-')
        self.replyStore = self.store.prefixed_db(b'R-')

    def getLastReqId(self):
        reqIds = [int(x) for x in self.reqStore.iterator(include_value=False)]
        return max(reqIds) if len(reqIds) > 0 else 0

    def addRequest(self, req):
        self.reqStore.put(str(req.reqId).encode(), pickle.dumps(req.__dict__))

    def addAck(self, reqId: int, sender: str):
        self.ackStore.put("{}-{}".format(reqId, sender).encode(), b'1')

    def addReply(self, reqId: int, sender: str, result: Any):
        self.replyStore.put("{}-{}".format(reqId, sender).encode(),
                            pickle.dumps(result))

    @classmethod
    def getDataLocation(cls, clientId):
        return os.path.join(cls.currentPath, cls.dataLocation, clientId)
