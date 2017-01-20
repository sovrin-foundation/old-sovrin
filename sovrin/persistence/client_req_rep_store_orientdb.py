from typing import Any, Sequence, List

from plenum.common.txn import TXN_ID
from plenum.common.txn import TXN_TYPE, TXN_TIME
from plenum.common.types import f
from plenum.common.util import checkIfMoreThanFSameItems, getMaxFailures, \
    updateFieldsWithSeqNo
from plenum.persistence.orientdb_store import OrientDbStore

from sovrin.common.txn import getTxnOrderedFields
from sovrin.common.types import Request
from sovrin.persistence.client_req_rep_store import ClientReqRepStore

REQ_DATA = "ReqData"
"""
The attribute data stored by the client differs from that of the node in
that the client stored the attribute key and value in a non-encrypted form
 and also store the secret key used to encrypt the data.
This will change once Wallet is implemented.
"""

LAST_TXN_DATA = "LastTxnData"


class ClientReqRepStoreOrientDB(ClientReqRepStore):
    def __init__(self, store: OrientDbStore):
        self.store = store
        self.bootstrap()

    @property
    def classesNeeded(self):
        return [
            (REQ_DATA, self.createReqDataClass),
            (LAST_TXN_DATA, self.createLastTxnClass)
        ]

    def bootstrap(self):
        self.store.createClasses(self.classesNeeded)

    @property
    def txnFieldOrdering(self):
        fields = getTxnOrderedFields()
        return updateFieldsWithSeqNo(fields)

    def createLastTxnClass(self):
        self.store.createClass(LAST_TXN_DATA)
        self.store.createClassProperties(LAST_TXN_DATA, {
            f.IDENTIFIER.nm: "string",
            "value": "string",
        })
        self.store.createUniqueIndexOnClass(LAST_TXN_DATA, f.IDENTIFIER.nm)

    def createReqDataClass(self):
        self.store.createClass(REQ_DATA)
        self.store.createClassProperties(REQ_DATA, {
            f.REQ_ID.nm: "long",
            f.IDENTIFIER.nm: "string",
            TXN_TYPE: "string",
            TXN_ID: "string",
            TXN_TIME: "datetime",
            "acks": "embeddedset string",
            "nacks": "embeddedmap string",
            "replies": "embeddedmap string",
            "hasConsensus": "boolean"
        })
        self.store.createIndexOnClass(REQ_DATA, "hasConsensus")

    @property
    def lastReqId(self):
        result = self.store.client.command("select max({}) as lastId from {}".
                                           format(f.REQ_ID.nm, REQ_DATA))
        return 0 if not result else result[0].oRecordData['lastId']

    def addRequest(self, req: Request):
        self.store.client.command(
            "insert into {} set {} = {}, {} = '{}',{} = '{}', "
            "nacks = {{}}, replies = {{}}".
            format(REQ_DATA, f.REQ_ID.nm, req.reqId,
                   f.IDENTIFIER.nm, req.identifier,
                   TXN_TYPE, req.operation[TXN_TYPE]))

    def addAck(self, msg: Any, sender: str):
        identifier = msg[f.IDENTIFIER.nm]
        reqId = msg[f.REQ_ID.nm]
        self.store.client.command(
            "update {} add acks = '{}' where {} = '{}' and {} = {}".
            format(REQ_DATA, sender, f.IDENTIFIER.nm, identifier, f.REQ_ID.nm,
                   reqId))

    def addNack(self, msg: Any, sender: str):
        identifier = msg[f.IDENTIFIER.nm]
        reqId = msg[f.REQ_ID.nm]
        reason = msg[f.REASON.nm]
        reason = reason.replace('"', '\\"').replace("'", "\\'")
        self.store.client.command(
            "update {} set nacks.{} = '{}' where {} = '{}' and {} = {}".
            format(REQ_DATA, sender, reason, f.IDENTIFIER.nm, identifier,
                   f.REQ_ID.nm,
                   reqId))

    def addReply(self, identifier: str, reqId: int, sender: str, result: Any) -> \
            Sequence[str]:
        txnId = result[TXN_ID]
        txnTime = result.get(TXN_TIME)
        serializedTxn = self.txnSerializer.serialize(result, toBytes=False)
        serializedTxn = serializedTxn.replace('"', '\\"').replace("'", "\\'")
        res = self.store.client.command(
            "update {} set replies.{} = '{}' return "
            "after @this.replies where {} = '{}' and {} = {}".
            format(REQ_DATA, sender, serializedTxn, f.IDENTIFIER.nm, identifier,
                   f.REQ_ID.nm, reqId))
        replies = res[0].oRecordData['value']
        # TODO: Set txnId txnTime, txnType only when got same f+1 replies
        if len(replies) == 1:
            self.store.client.command(
                "update {} set {} = '{}', {} = {}, {} = '{}' "
                "where {} = '{}' and {} = {}".
                format(REQ_DATA, TXN_ID, txnId, TXN_TIME,
                       txnTime, TXN_TYPE, result[TXN_TYPE],
                       f.IDENTIFIER.nm, identifier,
                       f.REQ_ID.nm, reqId))
        return len(replies)

    def requestConfirmed(self, identifier, reqId):
        result = self.store.client.command(
            "select {} from {} where {} = '{}' and {} = {}".
            format(TXN_ID, REQ_DATA, f.IDENTIFIER.nm, identifier, f.REQ_ID.nm,
                   reqId))
        return bool(result[0].oRecordData.get(TXN_ID) if result else False)

    def hasRequest(self, identifier: str, reqId: int):
        result = self.store.client.command(
            "select from {} where {} = '{}' and {} = {}".
            format(REQ_DATA, f.IDENTIFIER.nm, identifier, f.REQ_ID.nm, reqId))
        return bool(result)

    def getReplies(self, identifier: str, reqId: int):
        result = self.store.client.command(
            "select replies from {} where {} = '{}' and {} = {}".
            format(REQ_DATA, f.IDENTIFIER.nm, identifier, f.REQ_ID.nm, reqId))
        if not result:
            return {}
        else:
            return {
                k: self.txnSerializer.deserialize(v)
                for k, v in result[0].oRecordData['replies'].items()
                }

    def getAcks(self, identifier: str, reqId: int) -> List[str]:
        result = self.store.client.command(
            "select acks from {} where {} = '{}' and {} = {}".
            format(REQ_DATA, f.IDENTIFIER.nm, identifier, f.REQ_ID.nm, reqId))
        if not result:
            return []
        result = result[0].oRecordData.get('acks', [])
        return result

    def getNacks(self, identifier: str, reqId: int) -> dict:
        result = self.store.client.command(
            "select nacks from {} where {} = '{}' and {} = {}".
            format(REQ_DATA, f.IDENTIFIER.nm, identifier, f.REQ_ID.nm, reqId))
        return {} if not result else result[0].oRecordData.get('nacks', {})

    def setConsensus(self, identifier: str, reqId: int, value='true'):
        self.store.client.command(
            "update {} set hasConsensus = {} where {} = '{}' and {} = {}".
            format(REQ_DATA, value, f.IDENTIFIER.nm, identifier, f.REQ_ID.nm,
                   reqId))

    def hasConsensus(self, identifier: str, reqId: int):
        result = self.store.client.command("select hasConsensus from {} where "
                                           "{} = '{}' and {} = {}".format(
            REQ_DATA, f.IDENTIFIER.nm, identifier, f.REQ_ID.nm,
            reqId))
        if result and result[0].oRecordData.get('hasConsensus'):
            replies = self.getReplies(identifier, reqId).values()
            fVal = getMaxFailures(len(list(replies)))
            return checkIfMoreThanFSameItems(replies, fVal)
        else:
            return False

    def setLastTxnForIdentifier(self, identifier, value: str):
        self.store.client.command(
            "update {} set value = '{}', {} = '{}' upsert "
            "where {} = '{}'".
            format(LAST_TXN_DATA, value, f.IDENTIFIER.nm,
                   identifier, f.IDENTIFIER.nm, identifier))

    def getLastTxnForIdentifier(self, identifier):
        result = self.store.client.command(
            "select value from {} where {} = '{}'".
            format(LAST_TXN_DATA, f.IDENTIFIER.nm,
                   identifier))
        return None if not result else result[0].oRecordData['value']
