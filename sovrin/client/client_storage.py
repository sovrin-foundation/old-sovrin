import os
from typing import Any
import pickle

import plyvel

import sovrin
from plenum.common.request_types import f


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
        self.nackStore = self.store.prefixed_db(b'N-')
        self.replyStore = self.store.prefixed_db(b'R-')

    def getAllReqIds(self):
        return [int(x) for x in self.reqStore.iterator(include_value=False)]

    def getLastReqId(self):
        reqIds = self.getAllReqIds()
        return max(reqIds) if len(reqIds) > 0 else 0

    def addRequest(self, req):
        self.reqStore.put(str(req.reqId).encode(), pickle.dumps(req.__dict__))

    def addAck(self, msg: Any, sender: str):
        reqId = msg[f.REQ_ID.nm]
        self.ackStore.put("{}-{}".format(reqId, sender).encode(), b'1')

    def addNack(self, msg: int, sender: str):
        reqId = msg[f.REQ_ID.nm]
        reason = pickle.dumps(msg[f.REASON.nm])
        self.nackStore.put("{}-{}".format(reqId, sender).encode(), reason)

    def addReply(self, reqId: int, sender: str, result: Any):
        self.replyStore.put("{}-{}".format(reqId, sender).encode(),
                            pickle.dumps(result))

    @classmethod
    def getDataLocation(cls, clientName):
        return os.path.join(cls.currentPath, cls.dataLocation, clientName)

    def hasRequest(self, reqId: int):
        return reqId in self.getAllReqIds()

    def getRepliesFromAllNodes(self, reqId: int):
        result = {k.split(b'-')[1].decode(): pickle.loads(v)
                  for k, v in self.replyStore.iterator(prefix=str(reqId)
                                                               .encode())}
        return result

    def getErrorsFromAllNodes(self, reqId: int):
        result = {k.split(b'-')[1].decode(): pickle.loads(v)
                  for k, v in self.nackStore.iterator(prefix=str(reqId)
                                                               .encode())}
        return result

    def getAllReplies(self, reqId):
        replies = self.getRepliesFromAllNodes(reqId)
        errors = self.getErrorsFromAllNodes(reqId)
        return replies, errors
