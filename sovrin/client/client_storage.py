import json
import os
from typing import Any, Sequence

from ledger.serializers.compact_serializer import CompactSerializer
from ledger.stores.text_file_store import TextFileStore
from plenum.common.has_file_storage import HasFileStorage
from plenum.common.txn import TXN_TYPE, TARGET_NYM, TXN_TIME, TXN_ID
from plenum.common.types import Request, f
from sovrin.common.txn import getTxnOrderedFields
from sovrin.persistence.identity_graph import IdentityGraph, Edges, Vertices

REQ_DATA = "ReqData"
ATTR_DATA = "AttrData"
"""
The attribute data stored by the client differs from that of the node in
that the client stored the attribute key and value in a non-encrypted form
 and also store the secret key used to encrypt the data.
This will change once Wallet is implemented.
"""
LAST_TXN_DATA = "LastTxnData"

compactSerializer = CompactSerializer()
txnOrderedFields = getTxnOrderedFields()


def serializeTxn(data,
                 serializer=compactSerializer,
                 txnFields=txnOrderedFields):
    return serializer.serialize(data,
                                fields=txnFields,
                                toBytes=False)


def deserializeTxn(data,
                   serializer=compactSerializer,
                   fields=txnOrderedFields):
    return serializer.deserialize(data, fields)


class PrimaryStorage(HasFileStorage):
    """
    An immutable log of transactions made by a Sovrin client.
    """
    def __init__(self, clientName, baseDir=None):
        self.dataDir = "data/clients"
        self.name = clientName
        HasFileStorage.__init__(self, clientName,
                                baseDir=baseDir,
                                dataDir=self.dataDir)
        self.clientDataLocation = self.getDataLocation()
        if not os.path.exists(self.clientDataLocation):
            os.makedirs(self.clientDataLocation)
        self.transactionLog = TextFileStore(self.clientDataLocation,
                                            "transactions")

    def addToTransactionLog(self, reqId, txn):
        self.transactionLog.put(str(reqId), serializeTxn(txn))


class SecondaryStorage(IdentityGraph):
    """
    Using Orientdb graph storage to store client requests and transactions.
    """

    def classesNeeded(self):
        return [
            (Vertices.Nym, self.createNymClass),
            (Vertices.Steward, self.createStewardClass),
            (Vertices.Sponsor, self.createSponsorClass),
            (Vertices.User, self.createUserClass),
            (Vertices.Attribute, self.createAttributeClass),
            (Edges.AddsNym, self.createAddsNymClass),
            (Edges.AliasOf, self.createAliasOfClass),
            (Edges.Sponsors, self.createSponsorsClass),
            (Edges.AddsAttribute, self.createAddsAttributeClass),
            (Edges.HasAttribute, self.createHasAttributeClass),
            (LAST_TXN_DATA, self.createLastTxnClass),
            (ATTR_DATA, self.createClientAttributeClass()),
            (REQ_DATA, self.createReqDataClass()),
        ]

    def createLastTxnClass(self):
        self.client.command("create class {}".format(LAST_TXN_DATA))
        self.store.createClassProperties(LAST_TXN_DATA, {
            f.IDENTIFIER.nm: "string",
            "value": "string",
        })
        self.store.createUniqueIndexOnClass(LAST_TXN_DATA, f.IDENTIFIER.nm)

    def getLastReqId(self):
        result = self.client.command("select max({}) as lastId from {}".
                                     format(f.REQ_ID.nm, REQ_DATA))
        return 0 if not result else result[0].oRecordData['lastId']

    def addRequest(self, req: Request):
        self.client.command("insert into {} set {} = {}, {} = '{}',"
                            "{} = '{}', nacks = {{}}, replies = {{}}".
                            format(REQ_DATA, f.REQ_ID.nm, req.reqId,
                                   f.IDENTIFIER.nm, req.identifier,
                                   TXN_TYPE, req.operation[TXN_TYPE]))

    def addAck(self, msg: Any, sender: str):
        reqId = msg[f.REQ_ID.nm]
        self.client.command("update {} add acks = '{}' where {} = {}".
                            format(REQ_DATA, sender, f.REQ_ID.nm, reqId))

    def addNack(self, msg: Any, sender: str):
        reqId = msg[f.REQ_ID.nm]
        reason = msg[f.REASON.nm]
        reason = reason.replace('"', '\\"').replace("'", "\\'")
        self.client.command("update {} set nacks.{} = '{}' where {} = {}".
                            format(REQ_DATA, sender, reason,
                                   f.REQ_ID.nm, reqId))

    def addReply(self, reqId: int, sender: str, result: Any) -> \
            Sequence[str]:
        txnId = result[TXN_ID]
        txnTime = result[TXN_TIME]
        serializedTxn = serializeTxn(result)
        res = self.client.command("update {} set replies.{} = '{}' return "
                                  "after @this.replies where {} = {}".
                                  format(REQ_DATA, sender, serializedTxn,
                                         f.REQ_ID.nm, reqId))
        replies = res[0].oRecordData['value']
        # TODO: Handle malicious nodes sending incorrect response
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
                k: deserializeTxn(v)
                for k, v in result[0].oRecordData['replies'].items()
                }

    def getAcks(self, reqId: int) -> dict:
        # Returning a dictionary here just for consistency
        result = self.client.command("select acks from {} where {} = {}".
                                     format(REQ_DATA, f.REQ_ID.nm, reqId))
        if not result:
            return {}
        result = {k: 1 for k in result[0].oRecordData.get('acks', [])}
        return result

    def getNacks(self, reqId: int) -> dict:
        result = self.client.command("select nacks from {} where {} = {}".
                                     format(REQ_DATA, f.REQ_ID.nm, reqId))
        return {} if not result else result[0].oRecordData.get('nacks', {})

    def getAllReplies(self, reqId: int):
        replies = self.getReplies(reqId)
        errors = self.getNacks(reqId)
        return replies, errors

    def setConsensus(self, reqId: int, value='true'):
        self.client.command("update {} set hasConsensus = {} where {} = {}".
                            format(REQ_DATA, value, f.REQ_ID.nm, reqId))

    def setLastTxnForIdentifier(self, identifier, value: str):
        self.client.command("update {} set value = '{}', {} = '{}' upsert "
                            "where {} = '{}'".
                            format(LAST_TXN_DATA, value, f.IDENTIFIER.nm,
                                   identifier, f.IDENTIFIER.nm, identifier))

    def getLastTxnForIdentifier(self, identifier):
        result = self.client.command("select value from {} where {} = '{}'".
                                     format(LAST_TXN_DATA, f.IDENTIFIER.nm,
                                            identifier))
        return None if not result else result[0].oRecordData['value']

    def createReqDataClass(self):
        self.client.command("create class {}".format(REQ_DATA))
        self.store.createClassProperties(REQ_DATA, {
            f.REQ_ID.nm: "long",
            f.IDENTIFIER.nm: "string",
            TXN_TYPE: "string",
            TXN_ID: "string",
            TXN_TIME: "datetime",
            "acks": "embeddedset string",
            "nacks": "embeddedmap string",
            "replies": "embeddedmap string",
            "hasConsensus": "boolean",
            "attribute": "embedded {}".format(ATTR_DATA),
        })
        self.store.createIndexOnClass(REQ_DATA, "hasConsensus")

    # TODO Remove this class once wallet is implemented
    def createClientAttributeClass(self):
        self.client.command("create class {}".format(ATTR_DATA))
        self.store.createClassProperties(ATTR_DATA, {
            TARGET_NYM: "string",
            "name": "string",
            "value": "string",
            "skey": "string"
        })
        self.store.createIndexOnClass(ATTR_DATA, TARGET_NYM)

    def addClientAttribute(self, reqId, attrData):
        data = json.dumps(attrData)
        result = self.client.command("insert into {} content {}".
                                     format(ATTR_DATA, data))
        self.client.command("update {} set attribute = {} where {} = {}".
                            format(REQ_DATA, result[0].oRecordData,
                                   f.REQ_ID.nm, reqId))

    def getAttributeRequestForNym(self, nym, attrName, identifier=None):
        whereClause = "attribute.{} = '{}' and attribute.name = '{}'". \
            format(TARGET_NYM, nym, attrName)
        if identifier:
            whereClause += " and {} = '{}'".format(f.IDENTIFIER.nm,
                                                   identifier)
        cmd = "select from {} where {} order by {} desc limit 1". \
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


class ClientStorage(PrimaryStorage, SecondaryStorage):

    def __init__(self, name, baseDir, store):
        # Initialize both primary and secondary storage here.
        PrimaryStorage.__init__(self, name, baseDir)
        SecondaryStorage.__init__(self, store)
