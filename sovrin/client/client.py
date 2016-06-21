import json
import os
from _sha256 import sha256
from base64 import b64decode
from collections import deque
from copy import deepcopy
from typing import Mapping, List, Dict, Union, Tuple

import base58
import pyorient
from pyorient import PyOrientCommandException

from raet.raeting import AutoMode
from sovrin.client import roles
from plenum.client.client import Client as PlenumClient
from plenum.server.router import Router
from plenum.client.signer import Signer
from plenum.common.startable import Status
from plenum.common.stacked import SimpleStack
from plenum.common.txn import REQACK, REPLY, REQNACK, STEWARD, TXN_TIME, ENC, \
    HASH, RAW, NAME, VERSION, KEYS, TYPE, IP, PORT
from plenum.common.types import OP_FIELD_NAME, Request, f, HA
from plenum.common.util import getlogger, getMaxFailures, \
    getSymmetricallyEncryptedVal, libnacl, error
from plenum.persistence.orientdb_store import OrientDbStore
from sovrin.client.client_storage import ClientStorage, deserializeTxn
from sovrin.client.wallet import Wallet
from sovrin.common.txn import TXN_TYPE, ATTRIB, DATA, TXN_ID, TARGET_NYM, SKEY, \
    DISCLO, NONCE, ORIGIN, GET_ATTR, GET_NYM, REFERENCE, USER, ROLE, \
    SPONSOR, NYM, GET_TXNS, LAST_TXN, TXNS, GET_TXN, CRED_DEF
from sovrin.common.util import getConfig
from sovrin.persistence.identity_graph import IdentityGraph, getEdgeFromType
from anoncreds.protocol.issuer import Issuer
from anoncreds.protocol.prover import Prover
from anoncreds.protocol.verifier import Verifier
from sovrin.persistence.wallet_storage_file import WalletStorageFile

logger = getlogger()


class Client(PlenumClient, Issuer, Prover, Verifier):
    def __init__(self,
                 name: str,
                 nodeReg: Dict[str, HA]=None,
                 ha: Union[HA, Tuple[str, int]]=None,
                 peerHA: Union[HA, Tuple[str, int]]=None,
                 lastReqId: int=0,
                 signer: Signer=None,
                 signers: Dict[str, Signer]=None,
                 basedirpath: str=None,
                 wallet: Wallet = None):
        clientDataDir = os.path.join(basedirpath, "data", "clients", name)
        wallet = wallet or \
                 Wallet(WalletStorageFile(clientDataDir))  # type: Wallet
        super().__init__(name,
                         nodeReg,
                         ha,
                         lastReqId,
                         signer,
                         signers,
                         basedirpath,
                         wallet)
        self.storage = self.getStorage(basedirpath)
        self.lastReqId = self.storage.getLastReqId()
        # TODO: Should I store values of attributes as non encrypted
        # Dictionary of attribute requests
        # Key is request id and values are stored as tuple of 5 elements
        # identifier, toNym, secretKey, attribute name, txnId
        # self.attributeReqs = self.storage.loadAttributes()
        # type: Dict[int, List[Tuple[str, str, str, str, str]]]
        self.autoDiscloseAttributes = False
        self.requestedPendingTxns = False
        Issuer.__init__(self, self.defaultIdentifier)
        # TODO nym should be not used as id of Prover and Verifier
        Prover.__init__(self, self.defaultIdentifier)
        Verifier.__init__(self, self.defaultIdentifier)
        dataDirs = ["data/{}s".format(r) for r in roles]

        # To make anonymous credentials optional, we may have a subclass
        #  of Sovrin Client instead that mixes in Issuer, Prover and
        #  Verifier.
        self.hasAnonCreds = bool(peerHA)
        if self.hasAnonCreds:
            self.peerHA = peerHA if isinstance(peerHA, HA) else HA(*peerHA)
            stackargs = dict(name=name,
                             ha=peerHA,
                             main=True,
                             auto=AutoMode.always)
            self.peerMsgRoutes = []
            self.peerMsgRouter = Router(*self.peerMsgRoutes)
            self.peerStack = SimpleStack(stackargs,
                                         msgHandler=self.handlePeerMessage)
            self.peerStack.sign = self.sign
            self.peerInbox = deque()

    def handlePeerMessage(self, msg):
        """
        Use the peerMsgRouter to pass the messages to the correct
         function that handles them

        :param msg: the P2P client message.
        """
        return self.peerMsgRouter.handle(msg)

    def setupDefaultSigner(self):
        # Sovrin clients should use a wallet, which supplies the signers
        pass

    def sign(self, msg: Dict, signer: Signer) -> Dict:
        if msg["operation"].get(TXN_TYPE) == ATTRIB:
            msgCopy = deepcopy(msg)
            keyName = {RAW, ENC, HASH}.intersection(
                set(msgCopy["operation"].keys())).pop()
            msgCopy["operation"][keyName] = sha256(msgCopy["operation"][keyName]
                                                   .encode()).hexdigest()
            msg[f.SIG.nm] = signer.sign(msgCopy)
            return msg
        else:
            return super().sign(msg, signer)

    # TODO: Why is it here if not used?
    def getGraphStorage(self, name):
        config = getConfig()
        return IdentityGraph(OrientDbStore(
            user=config.OrientDB["user"],
            password=config.OrientDB["password"],
            dbName=name,
            dbType=pyorient.DB_TYPE_GRAPH,
            storageType=pyorient.STORAGE_TYPE_PLOCAL))

    def getStorage(self, baseDirPath=None):
        config = getConfig()
        store = OrientDbStore(user=config.OrientDB["user"],
                              password=config.OrientDB["password"],
                              dbName=self.name,
                              storageType=pyorient.STORAGE_TYPE_PLOCAL)
        return ClientStorage(self.name, baseDirPath, store)

    def submit(self, *operations: Mapping, identifier: str=None) -> \
            List[Request]:
        # keys = []
        # attributeNames = []
        # attributeVals = []
        for op in operations:
            if op[TXN_TYPE] == ATTRIB:
                if not (RAW in op or ENC in op or HASH in op):
                    error("An operation must have one of these keys: {} or {} {}"
                          .format(RAW, ENC, HASH))

                # TODO: Consider encryption type too.
                if ENC in op:
                    anm = list(json.loads(op[ENC]).keys())[0]
                    encVal, secretKey = getSymmetricallyEncryptedVal(op[ENC])
                    # attributeNames.append(anm)
                    # keys.append(secretKey)
                    # attributeVals.append(op[ENC])
                    op[ENC] = encVal
                    self.wallet.addAttribute(name=anm, val=encVal,
                                             origin=op[ORIGIN],
                                             dest=op.get(TARGET_NYM),
                                             encKey=secretKey)
                # TODO: Consider hash type too.
                elif HASH in op:
                    data = json.loads(op[HASH])
                    anm = list(data.keys())[0]
                    aval = list(data.values())[0]
                    hashed = sha256(aval.encode()).hexdigest()
                    op[HASH] = {anm: hashed}
                    # attributeVals.append(op[HASH])
                    self.wallet.addAttribute(name=anm, val=aval,
                                             origin=op[ORIGIN],
                                             dest=op.get(TARGET_NYM),
                                             hashed=True)
                else:
                    data = json.loads(op[RAW])
                    anm = list(data.keys())[0]
                    aval = list(data.values())[0]
                    self.wallet.addAttribute(name=anm, val=aval,
                                             origin=op[ORIGIN],
                                             dest=op.get(TARGET_NYM))
                    # attributeNames.append(anm)
                    # attributeVals.append(op[RAW])
                # data = op[DATA]
                # encVal, secretKey = getSymmetricallyEncryptedVal(data)
                # op[DATA] = encVal
        requests = super().submit(*operations, identifier=identifier)
        for r in requests:
            self.storage.addRequest(r)
        #     operation = r.operation
        #     # If add attribute transaction then store encryption key and
        #     # attribute name with the request id for the attribute
        #     if operation[TXN_TYPE] == ATTRIB:
        #         attrData = {}
        #         if operation.get(TARGET_NYM):
        #             attrData[TARGET_NYM] = operation.get(TARGET_NYM)
        #         attrData = {
        #             TARGET_NYM: operation[TARGET_NYM],
        #             NAME: attributeNames.pop(0),
        #             "value": attributeVals.pop(0),
        #             SKEY: keys.pop(0)
        #         }
        #         self.storage.addClientAttribute(r.reqId, attrData)
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
            # TODO Should request be marked as hasConsensus in the storage?
            # Might be inefficient to compute f on every reply
            fVal = getMaxFailures(len(self.nodeReg))
            if len(replies) == fVal + 1:
                self.storage.setConsensus(reqId)
                if result[TXN_TYPE] == NYM:
                    self.addNymToGraph(result)
                elif result[TXN_TYPE] == ATTRIB:
                    self.storage.addAttribute(frm=result[ORIGIN],
                                              txnId=result[TXN_ID],
                                              txnTime=result[TXN_TIME],
                                              raw=result.get(RAW),
                                              enc=result.get(ENC),
                                              hash=result.get(HASH),
                                              to=result.get(TARGET_NYM)
                                              )
                elif result[TXN_TYPE] == GET_NYM:
                    if DATA in result and result[DATA]:
                        try:
                            self.addNymToGraph(json.loads(result[DATA]))
                        except PyOrientCommandException as ex:
                            logger.error(
                                "An exception was raised while adding "
                                "nym {}".format(ex))
                elif result[TXN_TYPE] == GET_TXNS:
                    if DATA in result and result[DATA]:
                        data = json.loads(result[DATA])
                        self.storage.setLastTxnForIdentifier(result[ORIGIN],
                                                             data[LAST_TXN])
                        for txn in data[TXNS]:
                            if txn[TXN_TYPE] == NYM:
                                self.addNymToGraph(txn)
                            elif txn[TXN_TYPE] == ATTRIB:
                                try:
                                    self.storage.addAttribute(frm=txn[ORIGIN],
                                              txnId=txn[TXN_ID],
                                              txnTime=txn[TXN_TIME],
                                              raw=txn.get(RAW),
                                              enc=txn.get(ENC),
                                              hash=txn.get(HASH),
                                              to=txn.get(TARGET_NYM)
                                              )
                                except pyorient.PyOrientCommandException as ex:
                                    logger.error(
                                        "An exception was raised while adding "
                                        "attribute {}".format(ex))

                elif result[TXN_TYPE] == CRED_DEF:
                    data = result.get(DATA)
                    self.storage.addCredDef(frm=result[ORIGIN],
                                            txnId=result[TXN_ID],
                                            txnTime=result[TXN_TIME],
                                            name=data.get(NAME),
                                            version=data.get(VERSION),
                                            keys=json.loads(data.get(KEYS)),   # TODO: Figure out a way to avoid this.
                                            typ=data.get(TYPE),
                                            ip=data.get(IP),
                                            port=data.get(PORT))

                if result[TXN_TYPE] in (NYM, ATTRIB, CRED_DEF):
                    self.storage.addToTransactionLog(reqId, result)
        else:
            logger.debug("Invalid op message {}".format(msg))

    def addNymToGraph(self, txn):
        if ROLE not in txn or txn[ROLE] == USER:
            if txn.get(ORIGIN) and not self.storage.hasNym(txn.get(ORIGIN)):
                logger.warn("While adding user, origin not found in the graph")
            try:
                self.storage.addUser(
                    txn.get(TXN_ID),
                    txn.get(TARGET_NYM),
                    txn.get(ORIGIN),
                    reference=txn.get(REFERENCE))
            except (pyorient.PyOrientCommandException,
                    pyorient.PyOrientORecordDuplicatedException) as ex:
                logger.error("An exception was raised while adding "
                             "user {}".format(ex))
        elif txn[ROLE] == SPONSOR:
            # Since only a steward can add a sponsor, check if the steward
            # is present. If not then add the steward
            if txn.get(ORIGIN) and \
                    not self.storage.hasSteward(txn.get(ORIGIN)):
                # A better way is to oo a GET_NYM for the steward.
                self.storage.addSteward(None, nym=txn.get(ORIGIN))
            try:
                self.storage.addSponsor(txn.get(TXN_ID),
                                             txn.get(TARGET_NYM),
                                             txn.get(ORIGIN))
            except (pyorient.PyOrientCommandException,
                    pyorient.PyOrientORecordDuplicatedException) as ex:
                logger.error(
                    "An exception was raised while adding "
                    "sponsor {}".format(ex))
        elif txn[ROLE] == STEWARD:
            try:
                self.storage.addSteward(txn.get(TXN_ID), nym=txn.get(TARGET_NYM),
                                        frm=txn.get(ORIGIN))
            except (pyorient.PyOrientCommandException,
                    pyorient.PyOrientORecordDuplicatedException) as ex:
                logger.error(
                    "An exception was raised while adding "
                    "steward {}".format(ex))
        else:
            raise ValueError("Unknown role for nym, cannot add nym to graph")

    def getTxnById(self, txnId: str):
        serTxn = list(self.storage.getRepliesForTxnIds(txnId).values())[0]
        # TODO Add merkleInfo as well
        return deserializeTxn(serTxn)

    def getTxnsByNym(self, nym: str):
        # TODO Implement this
        pass

    def getTxnsByType(self, txnType):
        edgeClass = getEdgeFromType(txnType)
        if edgeClass:
            cmd = "select from {}".format(edgeClass)
            result = self.storage.client.command(cmd)
            return result and [r.oRecordData for r in result]
        return []

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
            TXN_TYPE: DISCLO,
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
        walletAttribute = self.wallet.getAttribute(attrName, nym)
        if walletAttribute:
            if TARGET_NYM in walletAttribute and \
                            walletAttribute[TARGET_NYM] == nym:
                if RAW in walletAttribute:
                    if walletAttribute[NAME] == attrName:
                        return {walletAttribute[NAME]: walletAttribute[RAW]}
                elif ENC in walletAttribute:
                    attr = self._getDecryptedData(walletAttribute[ENC],
                                           walletAttribute[SKEY])
                    if attrName in attr:
                        return attr
                elif HASH in walletAttribute:
                    if walletAttribute[NAME] == attrName:
                        return {walletAttribute[NAME]: walletAttribute[HASH]}

        # attributeReq = self.storage.getAttributeRequestForNym(nym, attrName,
        #                                                       identifier)
        # if attributeReq is None:
        #     return None
        # reply, error = self.replyIfConsensus(attributeReq[f.REQ_ID.nm])
        # if reply is None:
        #     return None
        # else:
        #     return self._getDecryptedData(reply[DATA],
        #                                   attributeReq['attribute']['skey'])

    def getAllAttributesForNym(self, nym, identifier=None):
        walletAttributes = self.wallet.attributes
        attributes = []
        for attr in walletAttributes:
            if TARGET_NYM in attr and attr[TARGET_NYM] == nym:
                if RAW in attr:
                    attributes.append({attr[NAME]: attr[RAW]})
                elif ENC in attr:
                    attributes.append(self._getDecryptedData(attr[ENC], attr[SKEY]))
                elif HASH in attr:
                    attributes.append({attr[NAME]: attr[HASH]})
        # attributeReqs = self.storage.getAllAttributeRequestsForNym(nym,
        #                                                            identifier)
        # attributes = []
        # for req in attributeReqs.values():
        #     reply, error = self.replyIfConsensus(req[f.REQ_ID.nm])
        #     if reply is not None:
        #         attr = self._getDecryptedData(reply[DATA],
        #                                       req['attribute']['skey'])
        #         attributes.append(attr)
        return attributes

    def doGetNym(self, nym, identifier=None):
        identifier = identifier if identifier else self.defaultIdentifier
        op = {
            ORIGIN: identifier,
            TARGET_NYM: nym,
            TXN_TYPE: GET_NYM,
        }
        self.submit(op, identifier=identifier)

    def doGetTxn(self, txnId, identifier=None):
        identifier = identifier if identifier else self.defaultIdentifier
        op = {
            ORIGIN: identifier,
            TARGET_NYM: identifier,
            TXN_TYPE: GET_TXN,
            DATA: txnId
        }
        self.submit(op, identifier=identifier)

    def hasNym(self, nym):
        return self.storage.hasNym(nym)

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
            lastTxn = self.storage.getLastTxnForIdentifier(identifier)
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

    def start(self, loop):
        super().start(loop)
        if self.hasAnonCreds and \
                        self.status is not Status.going():
            self.peerStack.start()

    async def prod(self, limit) -> int:
        s = await self.nodestack.service(limit)
        if self.isGoing():
            await self.nodestack.serviceLifecycle()
        self.nodestack.flushOutBoxes()
        if self.hasAnonCreds:
            return s + await self.peerStack.service(limit)
        else:
            return s
