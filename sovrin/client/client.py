import json
from base64 import b64decode
from typing import Mapping, List, Any, Dict, Union, Tuple

import base58
import pyorient
from pyorient import PyOrientCommandException, PyOrientORecordDuplicatedException
from plenum.client.client import Client as PlenumClient
from plenum.client.signer import Signer
from plenum.common.types import OP_FIELD_NAME, Request, f, HA
from plenum.common.startable import Status
from plenum.common.txn import REQACK, REPLY, REQNACK
from plenum.common.util import getlogger, getMaxFailures, \
    getSymmetricallyEncryptedVal, libnacl
from plenum.persistence.orientdb_store import OrientDbStore

from sovrin.client.client_storage import ClientStorage
from sovrin.common.txn import TXN_TYPE, ADD_ATTR, DATA, TXN_ID, TARGET_NYM, SKEY, \
    DISCLOSE, NONCE, ORIGIN, GET_ATTR, GET_NYM, REFERENCE, USER, ROLE, \
    SPONSOR, ADD_NYM, GET_TXNS, LAST_TXN, TXNS
from sovrin.common.util import getConfig
from sovrin.persistence.graph_store import GraphStore

logger = getlogger()


class Client(PlenumClient):
    def __init__(self,
                 name: str,
                 nodeReg: Dict[str, HA]=None,
                 ha: Union[HA, Tuple[str, int]]=None,
                 lastReqId: int = 0,
                 signer: Signer=None,
                 signers: Dict[str, Signer]=None,
                 basedirpath: str=None):
        super().__init__(name,
                         nodeReg,
                         ha,
                         lastReqId,
                         signer,
                         signers,
                         basedirpath)
        self.graphStorage = self.getGraphStorage(name)
        self.storage = self.getStorage(basedirpath)
        self.lastReqId = self.storage.getLastReqId()
        # TODO: SHould i store values of attributes as non encrypted
        # Dictionary of attribute requests
        # Key is request id and values are stored as tuple of 5 elements
        # identifier, toNym, secretKey, attribute name, txnId
        # self.attributeReqs = self.storage.loadAttributes()
        # type: Dict[int, List[Tuple[str, str, str, str, str]]]
        self.autoDiscloseAttributes = False
        self.requestedPendingTxns = False

    def getGraphStorage(self, name):
        config = getConfig()
        return GraphStore(OrientDbStore(
            user=config.OrientDB["user"],
            password=config.OrientDB["password"],
            dbName=name,
            dbType=pyorient.DB_TYPE_GRAPH,
            storageType=pyorient.STORAGE_TYPE_PLOCAL))

    def setupDefaultSigner(self):
        # Sovrin clients should use a wallet, which supplies the signers
        pass

    def getStorage(self, baseDirPath=None):
        return ClientStorage(self.name, baseDirPath)

    def submit(self, *operations: Mapping, identifier: str=None) -> List[Request]:
        keys = []
        attributeNames = []
        attributeVals = []
        for op in operations:
            if op[TXN_TYPE] == ADD_ATTR:
                # Data is a json object with key as attribute name and value
                # as attribute value
                data = op[DATA]
                encVal, secretKey = getSymmetricallyEncryptedVal(data)
                op[DATA] = encVal
                keys.append(secretKey)
                anm = list(json.loads(data).keys())[0]
                attributeNames.append(anm)
                attributeVals.append(data)
        requests = super().submit(*operations, identifier=identifier)
        for r in requests:
            self.storage.addRequest(r)
            operation = r.operation
            # If add attribute transaction then store encryption key and
            # attribute name with the request id for the attribute
            if operation[TXN_TYPE] == ADD_ATTR:
                attrData = {
                    TARGET_NYM: operation[TARGET_NYM],
                    "name": attributeNames.pop(0),
                    "value": attributeVals.pop(0),
                    "skey": keys.pop(0)
                }
                self.storage.addAttribute(r.reqId, attrData)
        return requests

    def handleOneNodeMsg(self, wrappedMsg) -> None:
        super().handleOneNodeMsg(wrappedMsg)
        msg, sender = wrappedMsg
        if OP_FIELD_NAME not in msg:
            logger.error("Op absent in message {}".format(msg))
        elif msg[OP_FIELD_NAME] == REQACK:
            self.storage.addAck(msg, sender)
        elif msg[OP_FIELD_NAME] == REQNACK:
            self.storage.addNack(msg, sender)
        elif msg[OP_FIELD_NAME] == REPLY:
            result = msg[f.RESULT.nm]
            reqId = msg[f.RESULT.nm][f.REQ_ID.nm]
            if self.autoDiscloseAttributes:
                # TODO: This is just for now. As soon as the client finds out
                # that the attribute is added it discloses it
                # reqId = msg["reqId"]
                # if reqId in self.attributeReqs and not self.attributeReqs[
                #     reqId][-1]:
                #     origin = self.attributeReqs[reqId][0]
                #     key = self.atxnStorettributeReqs[reqId][2]
                #     txnId = result[TXN_ID]
                #     self.attributeReqs[reqId] += (txnId, )
                #     self.doAttrDisclose(origin, result[TARGET_NYM], txnId, key)
                pass
            replies = self.storage.addReply(reqId, sender, result)
            # TODO Should request be marked as consensed in the storage?
            # Might be inefficient to compute f on every reply
            fVal = getMaxFailures(len(self.nodeReg))
            if len(replies) == fVal + 1:
                self.storage.requestConsensed(reqId)
                if result[TXN_TYPE] == ADD_NYM:
                    self.addNymToGraph(result)
                elif result[TXN_TYPE] == ADD_ATTR:
                    self.graphStorage.addAttribute(frm=result[ORIGIN],
                                                   to=result[TARGET_NYM],
                                                   data=result[DATA],
                                                   txnId=result[TXN_ID])
                elif result[TXN_TYPE] == GET_NYM:
                    if DATA in result and result[DATA]:
                        try:
                            self.addNymToGraph(json.loads(result[DATA]))
                        except PyOrientCommandException as ex:
                            logger.error("An exception was raised while adding "
                                         "nym {}".format(ex))
                elif result[TXN_TYPE] == GET_TXNS:
                    if DATA in result and result[DATA]:
                        data = json.loads(result[DATA])
                        self.storage.setLastTxnForIdentifier(result[ORIGIN], data[LAST_TXN])
                        for txn in data[TXNS]:
                            if txn[TXN_TYPE] == ADD_NYM:
                                self.addNymToGraph(txn)
                            elif txn[TXN_TYPE] == ADD_ATTR:
                                try:
                                    self.graphStorage.addAttribute(
                                        frm=txn[ORIGIN],
                                        to=txn[TARGET_NYM],
                                        data=txn[DATA],
                                        txnId=txn[TXN_ID])
                                except pyorient.PyOrientCommandException as ex:
                                    logger.error(
                                        "An exception was raised while adding "
                                        "attribute {}".format(ex))

                if result[TXN_TYPE] in (ADD_NYM, ADD_ATTR):
                    self.storage.addToTransactionLog(reqId, result)
        else:
            logger.debug("Invalid op message {}".format(msg))

    def addNymToGraph(self, txn):
        if ROLE not in txn or txn[ROLE] == USER:
            if txn.get(ORIGIN) and not self.graphStorage.hasNym(txn.get(ORIGIN)):
                logger.warn("While adding user, origin not found in the graph")
            try:
                self.graphStorage.addUser(txn.get(TXN_ID), txn.get(TARGET_NYM),
                                  txn.get(ORIGIN), reference=txn.get(REFERENCE))
            except (pyorient.PyOrientCommandException,
                    pyorient.PyOrientORecordDuplicatedException) as ex:
                logger.error(
                    "An exception was raised while adding "
                    "user {}".format(ex))
        elif txn[ROLE] == SPONSOR:
            # Since only a steward can add a sponsor, check if the steward
            # is present. If not then add the steward
            if txn.get(ORIGIN) and not self.graphStorage.hasSteward(txn.get(ORIGIN)):
                # A better way is to oo a GET_NYM for the steward.
                self.graphStorage.addSteward(None, txn.get(ORIGIN))
            try:
                self.graphStorage.addSponsor(txn.get(TXN_ID),
                                             txn.get(TARGET_NYM),
                                             txn.get(ORIGIN))
            except (pyorient.PyOrientCommandException,
                    pyorient.PyOrientORecordDuplicatedException) as ex:
                logger.error(
                    "An exception was raised while adding "
                    "user {}".format(ex))
        else:
            raise ValueError("Unknown role for nym, cannot add nym to graph")

    def getTxnById(self, txnId: str):
        for v in self.storage.getRepliesByTxnId(txnId).values():
            result = self.storage.serializer.deserialize(
                v, fields=self.storage.txnFields)
            return result

    def getTxnsByNym(self, nym: str):
        # TODO Implement this
        pass

    def getTxnsByType(self, txnType):
        result = []
        f = getMaxFailures(len(self.nodeReg))
        for replies in self.storage.getRepliesByTxnType(txnType):
            if len(replies) > f:
                v = list(replies.values())[0]
                result.append(self.storage.serializer.deserialize(
                    v, fields=self.storage.txnFields))
        return result

    def hasMadeRequest(self, reqId: int):
        return self.storage.hasRequest(reqId)

    def replyIfConsensus(self, reqId: int):
        f = getMaxFailures(len(self.nodeReg))
        replies, errors = self.storage.getAllReplies(reqId)
        r = list(replies.values())[0] if len(replies) > f else None
        e = list(errors.values())[0] if len(errors) > f else None
        return r, e

    # TODO: Just for now. Remove it later
    def doAttrDisclose(self, origin, target, txnId, key):
        box = libnacl.public.Box(b64decode(origin), b64decode(target))

        data = json.dumps({TXN_ID: txnId, SKEY: key})
        nonce, boxedMsg = box.encrypt(data.encode(), pack_nonce=False)

        op = {
            ORIGIN: origin,
            TARGET_NYM: target,
            TXN_TYPE: DISCLOSE,
            NONCE: base58.b58encode(nonce),
            DATA: base58.b58encode(boxedMsg)
        }
        self.submit(op, identifier=origin)

    def doGetAttributeTxn(self, identifier, attrName):
        op = {
            ORIGIN: identifier,
            TARGET_NYM: identifier,
            TXN_TYPE: GET_ATTR,
            # TODO: Need to encrypt get query
            DATA: json.dumps({"name": attrName})
        }
        self.submit(op, identifier=identifier)

    @staticmethod
    def _getDecryptedData(encData, key):
        data = bytes(bytearray.fromhex(encData))
        rawKey = bytes(bytearray.fromhex(key))
        box = libnacl.secret.SecretBox(rawKey)
        decData = box.decrypt(data).decode()
        return json.loads(decData)

    def getAttributeForNym(self, nym, attrName, identifier=None):
        attributeReq = self.storage.getAttributeRequestForNym(nym, attrName,
                                                              identifier)
        if attributeReq is None:
            return None
        reply, error = self.replyIfConsensus(attributeReq[f.REQ_ID.nm])
        if reply is None:
            return None
        else:
            return self._getDecryptedData(reply[DATA],
                                          attributeReq['attribute']['skey'])

    def getAllAttributesForNym(self, nym, identifier=None):
        attributeReqs = self.storage.getAllAttributeRequestsForNym(nym,
                                                                   identifier)
        attributes = []
        for req in attributeReqs.values():
            reply, error = self.replyIfConsensus(req[f.REQ_ID.nm])
            if reply is not None:
                attr = self._getDecryptedData(reply[DATA],
                                              req['attribute']['skey'])
                attributes.append(attr)

        return attributes

    def doGetNym(self, nym, identifier=None):
        identifier = identifier if identifier else self.defaultIdentifier
        op = {
            ORIGIN: identifier,
            TARGET_NYM: nym,
            TXN_TYPE: GET_NYM,
        }
        self.submit(op, identifier=identifier)

    def hasNym(self, nym):
        return self.graphStorage.hasNym(nym)

    def isRequestSuccessful(self, reqId):
        acks = self.storage.getAcks(reqId)
        nacks = self.storage.getNacks(reqId)
        f = getMaxFailures(len(self.nodeReg))
        if len(acks) > f:
            return True, "Done"
        elif len(nacks) > f:
            # TODO: What if the the nacks were different from each node?
            return False, list(nacks.values())[0]
        else:
            return None

    def requestPendingTxns(self):
        for identifier in self.signers:
            lastTxn = self.storage.getValueForIdentifier(identifier)
            op = {
                ORIGIN: identifier,
                TARGET_NYM: identifier,
                TXN_TYPE: GET_TXNS,
            }
            if lastTxn:
                op[DATA] = lastTxn
            self.submit(op, identifier=identifier)

    def _statusChanged(self, old, new):
        super()._statusChanged(old, new)
        if new == Status.started:
            if not self.requestedPendingTxns:
                self.requestPendingTxns()
                self.requestedPendingTxns = True
