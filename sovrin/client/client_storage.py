import os

from ledger.serializers.compact_serializer import CompactSerializer
from ledger.stores.text_file_store import TextFileStore
from plenum.common.has_file_storage import HasFileStorage
from sovrin.common.txn import getTxnOrderedFields
from sovrin.common.util import getConfig
from sovrin.persistence.client_req_rep_store_file import ClientReqRepStoreFile
from sovrin.persistence.client_req_rep_store_orientdb import \
    ClientReqRepStoreOrientDB
from sovrin.persistence.identity_graph import IdentityGraph, Edges, Vertices

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
        self.clientDataLocation = self.dataLocation
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

    # TODO: Why it is here too?
    @property
    def classesNeeded(self):
        return [
            (Vertices.Nym, self.createNymClass),
            (Vertices.Attribute, self.createAttributeClass),
            (Vertices.CredDef, self.createCredDefClass),
            (Edges.AddsNym, self.createAddsNymClass),
            (Edges.AliasOf, self.createAliasOfClass),
            (Edges.AddsAttribute, self.createAddsAttributeClass),
            (Edges.HasAttribute, self.createHasAttributeClass),
            # (LAST_TXN_DATA, self.createLastTxnClass),
            # (REQ_DATA, self.createReqDataClass),
            (Edges.AddsCredDef, self.createAddsCredDefClass)
        ]

    # def createLastTxnClass(self):
    #     self.client.command("create class {}".format(LAST_TXN_DATA))
    #     self.store.createClassProperties(LAST_TXN_DATA, {
    #         f.IDENTIFIER.nm: "string",
    #         "value": "string",
    #     })
    #     self.store.createUniqueIndexOnClass(LAST_TXN_DATA, f.IDENTIFIER.nm)
    #
    # @property
    # def lastReqId(self):
    #     result = self.client.command("select max({}) as lastId from {}".
    #                                  format(f.REQ_ID.nm, REQ_DATA))
    #     return 0 if not result else result[0].oRecordData['lastId']
    #
    # def addRequest(self, req: Request):
    #     self.client.command("insert into {} set {} = {}, {} = '{}',{} = '{}', "
    #                         "nacks = {{}}, replies = {{}}".
    #                         format(REQ_DATA, f.REQ_ID.nm, req.reqId,
    #                                f.IDENTIFIER.nm, req.identifier,
    #                                TXN_TYPE, req.operation[TXN_TYPE]))
    #
    # def addAck(self, msg: Any, sender: str):
    #     reqId = msg[f.REQ_ID.nm]
    #     self.client.command("update {} add acks = '{}' where {} = {}".
    #                         format(REQ_DATA, sender, f.REQ_ID.nm, reqId))
    #
    # def addNack(self, msg: Any, sender: str):
    #     reqId = msg[f.REQ_ID.nm]
    #     reason = msg[f.REASON.nm]
    #     reason = reason.replace('"', '\\"').replace("'", "\\'")
    #     self.client.command("update {} set nacks.{} = '{}' where {} = {}".
    #                         format(REQ_DATA, sender, reason,
    #                                f.REQ_ID.nm, reqId))
    #
    # def addReply(self, reqId: int, sender: str, result: Any) -> \
    #         Sequence[str]:
    #     txnId = result[TXN_ID]
    #     txnTime = result.get(TXN_TIME)
    #     serializedTxn = serializeTxn(result)
    #     serializedTxn = serializedTxn.replace('"', '\\"').replace("'", "\\'")
    #     res = self.client.command("update {} set replies.{} = '{}' return "
    #                               "after @this.replies where {} = {}".
    #                               format(REQ_DATA, sender, serializedTxn,
    #                                      f.REQ_ID.nm, reqId))
    #     replies = res[0].oRecordData['value']
    #     # TODO: Handle malicious nodes sending incorrect response
    #     if len(replies) == 1:
    #         self.client.command("update {} set {} = '{}', {} = {}, {} = '{}' "
    #                             "where {} = {}".
    #                             format(REQ_DATA, TXN_ID, txnId, TXN_TIME,
    #                                    txnTime, TXN_TYPE, result[TXN_TYPE],
    #                                    f.REQ_ID.nm, reqId))
    #     return len(replies)
    #
    # def hasRequest(self, reqId: int):
    #     result = self.client.command("select from {} where {} = {}".
    #                                  format(REQ_DATA, f.REQ_ID.nm, reqId))
    #     return bool(result)
    #
    # def getReplies(self, reqId: int):
    #     result = self.client.command("select replies from {} where {} = {}".
    #                                  format(REQ_DATA, f.REQ_ID.nm, reqId))
    #     if not result:
    #         return {}
    #     else:
    #         return {
    #             k: deserializeTxn(v)
    #             for k, v in result[0].oRecordData['replies'].items()
    #             }
    #
    # def getAcks(self, reqId: int) -> List[str]:
    #     # Returning a dictionary here just for consistency
    #     result = self.client.command("select acks from {} where {} = {}".
    #                                  format(REQ_DATA, f.REQ_ID.nm, reqId))
    #     if not result:
    #         return []
    #     result = result[0].oRecordData.get('acks', [])
    #     return result
    #
    # def getNacks(self, reqId: int) -> dict:
    #     result = self.client.command("select nacks from {} where {} = {}".
    #                                  format(REQ_DATA, f.REQ_ID.nm, reqId))
    #     return {} if not result else result[0].oRecordData.get('nacks', {})
    #
    # def getAllReplies(self, reqId: int):
    #     replies = self.getReplies(reqId)
    #     errors = self.getNacks(reqId)
    #     return replies, errors
    #
    # def setConsensus(self, reqId: int, value='true'):
    #     self.client.command("update {} set hasConsensus = {} where {} = {}".
    #                         format(REQ_DATA, value, f.REQ_ID.nm, reqId))
    #
    # def setLastTxnForIdentifier(self, identifier, value: str):
    #     self.client.command("update {} set value = '{}', {} = '{}' upsert "
    #                         "where {} = '{}'".
    #                         format(LAST_TXN_DATA, value, f.IDENTIFIER.nm,
    #                                identifier, f.IDENTIFIER.nm, identifier))
    #
    # def getLastTxnForIdentifier(self, identifier):
    #     result = self.client.command("select value from {} where {} = '{}'".
    #                                  format(LAST_TXN_DATA, f.IDENTIFIER.nm,
    #                                         identifier))
    #     return None if not result else result[0].oRecordData['value']
    #
    # def createReqDataClass(self):
    #     self.client.command("create class {}".format(REQ_DATA))
    #     self.store.createClassProperties(REQ_DATA, {
    #         f.REQ_ID.nm: "long",
    #         f.IDENTIFIER.nm: "string",
    #         TXN_TYPE: "string",
    #         TXN_ID: "string",
    #         TXN_TIME: "datetime",
    #         "acks": "embeddedset string",
    #         "nacks": "embeddedmap string",
    #         "replies": "embeddedmap string",
    #         "hasConsensus": "boolean"
    #     })
    #     self.store.createIndexOnClass(REQ_DATA, "hasConsensus")


class ClientStorage:

    def __init__(self, name, baseDir, store):
        # Initialize both primary and secondary storage here.
        config = getConfig()
        self.txnStore = PrimaryStorage(name, baseDir)
