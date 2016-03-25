import os
from typing import Any

from plenum.common.request_types import f

from ledger.immutable_store.base64_serializer import Base64Serializer
from ledger.immutable_store.text_file_store import TextFileStore

from sovrin.common.has_file_storage import HasFileStorage


class ClientStorage(HasFileStorage):

    def __init__(self, clientName):
        self.dataDir = "data/clients"
        self.name = clientName
        HasFileStorage.__init__(self, clientName, dataDir=self.dataDir)
        self.clientDataLocation = self.getDataLocation()
        if not os.path.exists(self.clientDataLocation):
            os.makedirs(self.clientDataLocation)
        self.reqStore = TextFileStore(self.clientDataLocation, "RQ")
        self.ackStore = TextFileStore(self.clientDataLocation, "A")
        self.nackStore = TextFileStore(self.clientDataLocation, "N")
        self.replyStore = TextFileStore(self.clientDataLocation, "R")
        self.serializer = Base64Serializer()

    def _serializeRequest(self, req):
        return self.serializer.serialize(req, toBytes=False)

    def _serializeResult(self, res):
        return self.serializer.serialize(res, toBytes=False)

    def getAllReqIds(self):
        return [int(x) for x in self.reqStore.iterator(include_value=False)]

    def getLastReqId(self):
        reqIds = self.getAllReqIds()
        return max(reqIds) if len(reqIds) > 0 else 0

    def addRequest(self, req):
        self.reqStore.put(str(req.reqId), self._serializeRequest(req.__dict__))

    def addAck(self, msg: Any, sender: str):
        reqId = msg[f.REQ_ID.nm]
        self.ackStore.put("{}-{}".format(reqId, sender), self.serializer.
                          serialize({"error": None}, toBytes=False))

    def addNack(self, msg: int, sender: str):
        reqId = msg[f.REQ_ID.nm]
        reason = {"error": msg[f.REASON.nm]}
        self.nackStore.put("{}-{}".format(reqId, sender), self.serializer.
                           serialize(reason, toBytes=False))

    def addReply(self, reqId: int, sender: str, result: Any):
        self.replyStore.put("{}-{}".format(reqId, sender),
                            self._serializeResult(result))

    def hasRequest(self, reqId: int):
        return reqId in self.getAllReqIds()

    def getReplies(self, reqId: int):
        result = {k.split('-')[1]: self.serializer.deserialize(v)
                  for k, v in self.replyStore.iterator(prefix=str(reqId))}
        return result

    def getAcks(self, reqId: int):
        # Returning a dictionary here just for consistency
        result = {k.split('-')[1]: 1
                  for k, v in self.ackStore.iterator(prefix=str(reqId))}
        return result

    def getNacks(self, reqId: int):
        result = {k.split('-')[1]: self.serializer.deserialize(v)
                  for k, v in self.nackStore.iterator(prefix=str(reqId))}
        return result

    def getAllReplies(self, reqId):
        replies = self.getReplies(reqId)
        errors = self.getNacks(reqId)
        return replies, errors
