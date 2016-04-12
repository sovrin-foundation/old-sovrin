import json
from collections import OrderedDict
from typing import Any

import pyorient

from ledger.immutable_store.serializers.compact_serializer import \
    CompactSerializer
from plenum.common.request_types import Request, f
from plenum.common.util import getlogger

from sovrin.common.txn import TXN_ID, TXN_TIME, TARGET_NYM, TXN_TYPE
from sovrin.persistence.document_store import DocumentStore

logger = getlogger()

REQ_DATA = "ReqData"
ATTR_DATA = "AttrData"
LAST_TXN_DATA = "LastTxnData"


class ClientDocumentStore(DocumentStore):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def classesNeeded(self):
        return [
            (ATTR_DATA, self.createAttributeClass),
            (REQ_DATA, self.createReqDataClass),
            (LAST_TXN_DATA, self.createLastTxnClass)
        ]

    def createClasses(self):
        super(DocumentStore, self).createClasses()

    def bootstrap(self):
        self.createClasses()

    def createAttributeClass(self):
        self.client.command("create class {}".format(ATTR_DATA))
        self.createClassProperties(ATTR_DATA, {
            TARGET_NYM: "string",
            "name": "string",
            "value": "string",
            "skey": "string"
        })
        self.createIndexOnClass(ATTR_DATA, TARGET_NYM)

    def createReqDataClass(self):
        self.client.command("create class {}".format(REQ_DATA))
        self.createClassProperties(REQ_DATA, {
            f.REQ_ID.nm: "long",
            f.IDENTIFIER.nm: "string",
            "acks": "embeddedset string",
            "nacks": "embeddedmap string",
            "replies": "embeddedmap string",
            TXN_TYPE: "string",
            TXN_ID: "string",
            TXN_TIME: "datetime",
            "serialNo": "long",
            "STH": "string",
            "auditInfo": "embeddedlist string",
            "attribute": "embedded {}".format(ATTR_DATA),
            "consensed": "boolean"
        })
        self.createUniqueIndexOnClass(REQ_DATA, TXN_ID)
        self.createUniqueIndexOnClass(REQ_DATA, "serialNo")
        self.createIndexOnClass(REQ_DATA, "consensed")

    def createLastTxnClass(self):
        self.client.command("create class {}".format(LAST_TXN_DATA))
        self.createClassProperties(LAST_TXN_DATA, {
            f.IDENTIFIER.nm: "string",
            "value": "string",
        })
        self.createUniqueIndexOnClass(LAST_TXN_DATA, f.IDENTIFIER.nm)

    def getLastReqId(self):
        result = self.client.command("select max({}) as lastId from {}".
                                     format(f.REQ_ID.nm, REQ_DATA))
        return 0 if not result else result[0].oRecordData['lastId']

    def addRequest(self, req: Request):
        self.client.command("insert into {} set {} = {}, {} = '{}', {} = '{}', nacks = {}, replies = {}".
                            format(REQ_DATA, f.REQ_ID.nm, req.reqId,
                                   f.IDENTIFIER.nm, req.identifier, TXN_TYPE,
                                   req.operation[TXN_TYPE], "{}", "{}"))

    def addAck(self, msg: Any, sender: str):
        reqId = msg[f.REQ_ID.nm]
        self.client.command("update {} add acks = '{}' where {} = {}".
                            format(REQ_DATA, sender, f.REQ_ID.nm, reqId))

    def addNack(self, msg: int, sender: str):
        reqId = msg[f.REQ_ID.nm]
        reason = msg[f.REASON.nm]
        reason = reason.replace('"', '\\"').replace("'", "\\'")
        self.client.command("update {} set nacks.{} = '{}' where {} = {}".
                            format(REQ_DATA, sender, reason, f.REQ_ID.nm, reqId))

    def addReply(self, reqId: int, sender: str, result: Any):
        txnId = result[TXN_ID]
        txnTime = result[TXN_TIME]
        serializedTxn = self._serializeTxn(result)
        res = self.client.command("update {} set replies.{} = '{}' return after @this.replies where {} = {}".
                            format(REQ_DATA, sender, serializedTxn,
                                   f.REQ_ID.nm, reqId))
        replies = res[0].oRecordData['value']
        # TODO: Handle maclicious nodes sending incorrect response
        # If first reply for the request then update txn id and txn time
        if len(replies) == 1:
            self.client.command("update {} set {} = '{}', {} = {}, {} = '{}' "
                                "where {} = {}".
                                format(REQ_DATA, TXN_ID, txnId, TXN_TIME,
                                       txnTime, TXN_TYPE, result[TXN_TYPE],
                                       f.REQ_ID.nm, reqId))
        return replies

    def hasRequest(self, reqId: int):
        result = self.client.command("select from {} where {} = {}".
                                     format(REQ_DATA, f.REQ_ID.nm, reqId))
        return bool(result)

    def getReplies(self, reqId: int):
        result = self.client.command("select replies from {} where {} = {}".
                                     format(REQ_DATA, f.REQ_ID.nm, reqId))
        if not result:
            return {}
        else:
            return {
                k: self.serializer.deserialize(v, orderedFields=self.txnFields)
                for k, v in result[0].oRecordData['replies'].items()
            }

    def getAcks(self, reqId: int):
        # Returning a dictionary here just for consistency
        result = self.client.command("select acks from {} where {} = {}".
                                     format(REQ_DATA, f.REQ_ID.nm, reqId))
        if not result:
            return {}
        result = {k: 1 for k in result[0].oRecordData['acks']}
        return result

    def getNacks(self, reqId: int):
        result = self.client.command("select nacks from {} where {} = {}".
                                     format(REQ_DATA, f.REQ_ID.nm, reqId))
        return {} if not result else result[0].oRecordData['nacks']

    def getAllReplies(self, reqId):
        replies = self.getReplies(reqId)
        errors = self.getNacks(reqId)
        return replies, errors

    def addAttribute(self, reqId, attrData):
        data = json.dumps(attrData)
        result = self.client.command("insert into {} content {}".
                                     format(ATTR_DATA, data))
        self.client.command("update {} set attribute = {} where {} = {}".
                            format(REQ_DATA, result[0].oRecordData, f.REQ_ID.nm, reqId))

    def getAttributeRequestForNym(self, nym, attrName, identifier=None):
        whereClause = "attribute.{} = '{}' and attribute.name = '{}'".\
            format(TARGET_NYM, nym, attrName)
        if identifier:
            whereClause += " and {} = '{}'".format(f.IDENTIFIER.nm, identifier)

        cmd = "select from {} where {} order by {} desc limit 1".\
            format(REQ_DATA, whereClause, TXN_TIME)

        result = self.client.command(cmd)
        return None if not result else result[0].oRecordData

    def getAllAttributeRequestsForNym(self, nym, identifier=None):
        whereClause = "attribute.{} = '{}'". \
            format(TARGET_NYM, nym)
        if identifier:
            whereClause += " and {} = '{}'".format(f.IDENTIFIER.nm, identifier)
        cmd = "select from {} where {} order by {} desc". \
            format(REQ_DATA, whereClause, TXN_TIME)
        # TODO: May be can use a better sql query using group by attribute name
        # and getting last attribute request of each group
        result = self.client.command(cmd)
        attributeReqs = {}  # Dict[str, Dict]
        for r in result:
            data = r.oRecordData
            if "attribute" in data and data["attribute"]["name"] \
                    not in attributeReqs:
                attributeReqs[data["attribute"]["name"]] = data
        return attributeReqs

    def requestConsensed(self, reqId):
        self.client.command("update {} set consensed = true where {} = {}".
                            format(REQ_DATA, f.REQ_ID.nm, reqId))

    def getRepliesByTxnId(self, txnId):
        result = self.client.command("select replies from {} where {} = '{}'".
                                     format(REQ_DATA, TXN_ID, txnId))
        return [] if not result else result[0].oRecordData['replies']

    def getRepliesByTxnType(self, txnType):
        result = self.client.command("select replies from {} where {} = '{}'".
                                     format(REQ_DATA, TXN_TYPE, txnType))

        return [] if not result else [r.oRecordData['replies'] for r in result]

    def setLastTxnForIdentifier(self, identifier, value):
        self.client.command("update {} set value = '{}', {} = '{}' upsert where {} = '{}'".
                            format(LAST_TXN_DATA, value, f.IDENTIFIER.nm,
                                   identifier, f.IDENTIFIER.nm, identifier))

    def getValueForIdentifier(self, identifier):
        result = self.client.command("select value from {} where {} = '{}'".
                                     format(LAST_TXN_DATA, f.IDENTIFIER.nm, identifier))
        return None if not result else result[0].oRecordData['value']
