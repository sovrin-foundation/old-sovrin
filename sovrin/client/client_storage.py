import os
from collections import OrderedDict
from typing import Any

from ledger.immutable_store.serializers import JsonSerializer
from ledger.immutable_store.serializers.compact_serializer import \
    CompactSerializer
from ledger.immutable_store.stores import TextFileStore
from plenum.common.request_types import f
from sovrin.common.has_file_storage import HasFileStorage


class ClientStorage(HasFileStorage):

    def __init__(self, clientName, baseDirPath=None):
        self.dataDir = "data/clients"
        self.name = clientName
        HasFileStorage.__init__(self, clientName,
                                baseDir=baseDirPath,
                                dataDir=self.dataDir)
        self.clientDataLocation = self.getDataLocation()
        if not os.path.exists(self.clientDataLocation):
            os.makedirs(self.clientDataLocation)
        self.reqStore = TextFileStore(self.clientDataLocation, "RQ")
        self.ackStore = TextFileStore(self.clientDataLocation, "A")
        self.nackStore = TextFileStore(self.clientDataLocation, "N")
        self.replyStore = TextFileStore(self.clientDataLocation, "R")
        self.attributeStore = TextFileStore(self.clientDataLocation, "AT")
        self.serializer = CompactSerializer()
        self.requestFields = OrderedDict([
            ("identifier", (str, str)),
            ("signature", (str, str)),
            ("reqId", (str, int)),
            ("operation.type", (str, str)),
            ("operation.origin", (str, str)),
            ("operation.dest", (str, str)),
            ("operation.data", (str, str)),
            ("operation.role", (str, str)),
            ("operation.reference", (str, str)),
        ])
        self.ackFields = OrderedDict([
            ("error", (str, str))
        ])
        self.nackFields = OrderedDict([
            ("error", (str, str))
        ])
        self.replyFields = OrderedDict([
            ("txnId", (str, str)),
            ("txnTime", (str, float)),
            ("type", (str, str)),
            ("origin", (str, str)),
            ("dest", (str, str)),
            ("data", (str, str)),
            ("role", (str, str)),
            ("reference", (str, str)),
        ])
        self.attrSerializer = JsonSerializer()

    def _serializeRequest(self, req):
        return self.serializer.serialize(req, orderedFields=self.requestFields,
                                         toBytes=False)

    def _serializeResult(self, res):
        return self.serializer.serialize(res, orderedFields=self.replyFields,
                                         toBytes=False)

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
                          serialize({"error": None}, orderedFields=self.ackFields,
                                    toBytes=False))

    def addNack(self, msg: int, sender: str):
        reqId = msg[f.REQ_ID.nm]
        reason = {"error": msg[f.REASON.nm]}
        self.nackStore.put("{}-{}".format(reqId, sender), self.serializer.
                           serialize(reason, orderedFields=self.nackFields,
                                     toBytes=False))

    def addReply(self, reqId: int, sender: str, result: Any):
        self.replyStore.put("{}-{}".format(reqId, sender),
                            self._serializeResult(result))

    def hasRequest(self, reqId: int):
        return reqId in self.getAllReqIds()

    def getReplies(self, reqId: int):
        result = {k.split('-')[1]: self.serializer.deserialize(v, orderedFields=self.replyFields)
                  for k, v in self.replyStore.iterator(prefix=str(reqId))}
        return result

    def getAcks(self, reqId: int):
        # Returning a dictionary here just for consistency
        result = {k.split('-')[1]: 1
                  for k, v in self.ackStore.iterator(prefix=str(reqId))}
        return result

    def getNacks(self, reqId: int):
        result = {k.split('-')[1]: self.serializer.deserialize(v, orderedFields=self.nackFields)
                  for k, v in self.nackStore.iterator(prefix=str(reqId))}
        return result

    def getAllReplies(self, reqId):
        replies = self.getReplies(reqId)
        errors = self.getNacks(reqId)
        return replies, errors

    def addAttribute(self, reqId, attrData):
        self.attributeStore.put(str(reqId), self.attrSerializer.serialize(attrData,
                                                                      toBytes=False))

    def loadAttributes(self):
        return {int(k): self.attrSerializer.deserialize(v)
                for k, v in self.attributeStore.iterator()}
