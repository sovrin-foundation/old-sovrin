import json
import os
from _sha256 import sha256
from base64 import b64decode
from collections import deque
from copy import deepcopy
from typing import Mapping, List, Dict, Union, Tuple

import base58
import pyorient

from raet.raeting import AutoMode
from sovrin.client import roles
from plenum.client.client import Client as PlenumClient
from plenum.server.router import Router
from plenum.client.signer import Signer
from plenum.common.startable import Status
from plenum.common.stacked import SimpleStack
from plenum.common.txn import REQACK, REPLY, REQNACK, STEWARD, ENC, \
    HASH, RAW, NAME, VERSION, KEYS, TYPE, IP, PORT
from plenum.common.types import OP_FIELD_NAME, Request, f, HA, OPERATION
from plenum.common.util import getlogger, getMaxFailures, \
    getSymmetricallyEncryptedVal, libnacl, error
from plenum.persistence.orientdb_store import OrientDbStore
from sovrin.client.client_storage import ClientStorage, deserializeTxn
from sovrin.client.wallet import Wallet
from sovrin.common.txn import TXN_TYPE, ATTRIB, DATA, TXN_ID, TARGET_NYM, SKEY,\
    DISCLO, NONCE, GET_ATTR, GET_NYM, ROLE, \
    SPONSOR, NYM, GET_TXNS, LAST_TXN, TXNS, GET_TXN, CRED_DEF, GET_CRED_DEF
from sovrin.common.util import getConfig
from sovrin.persistence.identity_graph import getEdgeFromTxnType
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

    def setupWallet(self, wallet=None):
        if wallet:
            self.wallet = wallet
        else:
            storage = WalletStorageFile.fromName(self.name, self.basedirpath)
            self.wallet = Wallet(self.name, storage)

    def handlePeerMessage(self, msg):
        """
        Use the peerMsgRouter to pass the messages to the correct
         function that handles them

        :param msg: the P2P client message.
        """
        return self.peerMsgRouter.handle(msg)

    def sign(self, msg: Dict, signer: Signer) -> Dict:
        if msg[OPERATION].get(TXN_TYPE) == ATTRIB:
            msgCopy = deepcopy(msg)
            keyName = {RAW, ENC, HASH}.intersection(
                set(msgCopy[OPERATION].keys())).pop()
            msgCopy[OPERATION][keyName] = sha256(msgCopy[OPERATION][keyName]
                                                   .encode()).hexdigest()
            msg[f.SIG.nm] = signer.sign(msgCopy)
            return msg
        else:
            return super().sign(msg, signer)

    def getStorage(self, baseDirPath=None):
        config = getConfig()
        store = OrientDbStore(user=config.OrientDB["user"],
                              password=config.OrientDB["password"],
                              dbName=self.name,
                              storageType=pyorient.STORAGE_TYPE_PLOCAL)
        return ClientStorage(self.name, baseDirPath, store)

    def submit(self, *operations: Mapping, identifier: str=None) -> \
            List[Request]:
        origin = identifier or self.defaultIdentifier
        for op in operations:
            if op[TXN_TYPE] == ATTRIB:
                if not (RAW in op or ENC in op or HASH in op):
                    error("An operation must have one of these keys: {} or {} {}"
                          .format(RAW, ENC, HASH))

                # TODO: Consider encryption type too.
                if ENC in op:
                    anm = list(json.loads(op[ENC]).keys())[0]
                    encVal, secretKey = getSymmetricallyEncryptedVal(op[ENC])
                    op[ENC] = encVal
                    self.wallet.addAttribute(name=anm, val=encVal,
                                             origin=origin,
                                             dest=op.get(TARGET_NYM),
                                             encKey=secretKey)
                # TODO: Consider hash type too.
                elif HASH in op:
                    data = json.loads(op[HASH])
                    anm = list(data.keys())[0]
                    aval = list(data.values())[0]
                    hashed = sha256(aval.encode()).hexdigest()
                    op[HASH] = {anm: hashed}
                    self.wallet.addAttribute(name=anm, val=aval,
                                             origin=origin,
                                             dest=op.get(TARGET_NYM),
                                             hashed=True)
                else:
                    data = json.loads(op[RAW])
                    anm = list(data.keys())[0]
                    aval = list(data.values())[0]
                    self.wallet.addAttribute(name=anm, val=aval,
                                             origin=origin,
                                             dest=op.get(TARGET_NYM))
            # TODO: When an issuer is submitting a cred def transaction, he
            # should add it to his wallet too
            # if op[TXN_TYPE] == CRED_DEF:
            #     self.wallet.addCredDef(data[NAME], data[VERSION],
            #                            result[TARGET_NYM], data[TYPE],
            #                            data[IP], data[PORT], keys)
        requests = super().submit(*operations, identifier=identifier)
        for r in requests:
            self.storage.addRequest(r)
        return requests

    def handleOneNodeMsg(self, wrappedMsg, excludeFromCli=None) -> None:
        msg, sender = wrappedMsg
        # Do not print result of transaction type `GET_TXNS` on the CLI
        excludeFromCli = excludeFromCli or (msg.get(OP_FIELD_NAME) == REPLY and
                                            msg[f.RESULT.nm][TXN_TYPE] == GET_TXNS)
        super().handleOneNodeMsg(wrappedMsg, excludeFromCli)
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
                    self.storage.addAttribTxnToGraph(result)
                elif result[TXN_TYPE] == GET_NYM:
                    if DATA in result and result[DATA]:
                        self.addNymToGraph(json.loads(result[DATA]))
                elif result[TXN_TYPE] == GET_TXNS:
                    if DATA in result and result[DATA]:
                        data = json.loads(result[DATA])
                        self.storage.setLastTxnForIdentifier(result[f.IDENTIFIER.nm],
                                                             data[LAST_TXN])
                        for txn in data[TXNS]:
                            if txn[TXN_TYPE] == NYM:
                                self.addNymToGraph(txn)
                            elif txn[TXN_TYPE] == ATTRIB:
                                try:
                                    self.storage.addAttribTxnToGraph(txn)
                                except pyorient.PyOrientCommandException as ex:
                                    logger.error(
                                        "An exception was raised while adding "
                                        "attribute {}".format(ex))

                elif result[TXN_TYPE] == CRED_DEF:
                    self.storage.addCredDefTxnToGraph(result)
                elif result[TXN_TYPE] == GET_CRED_DEF:
                    data = result.get(DATA)
                    try:
                        data = json.loads(data)
                        keys = json.loads(data[KEYS])
                    except Exception as ex:
                        # Checking if data was converted to JSON, if it was then
                        #  exception was raised while converting KEYS
                        # TODO: Check fails if data was a dictionary.
                        if isinstance(data, dict):
                            logger.error(
                                "Keys {} cannot be converted to JSON".format(data[KEYS]))
                        else:
                            logger.error("{} cannot be converted to JSON".format(data))
                    else:
                        self.wallet.addCredDef(data[NAME], data[VERSION],
                                               result[TARGET_NYM], data[TYPE],
                                               data[IP], data[PORT], keys)

                if result[TXN_TYPE] in (NYM, ATTRIB, CRED_DEF):
                    self.storage.addToTransactionLog(reqId, result)
        else:
            logger.debug("Invalid op message {}".format(msg))

    def addNymToGraph(self, txn):
        origin = txn.get(f.IDENTIFIER.nm)
        if txn.get(ROLE) == SPONSOR:
            if not self.storage.hasSteward(origin):
                self.storage.addNym(None, nym=origin, role=STEWARD)
        self.storage.addNymTxnToGraph(txn)

    def getTxnById(self, txnId: str):
        serTxn = list(self.storage.getResultForTxnIds(txnId).values())[0]
        # TODO Add merkleInfo as well
        return deserializeTxn(serTxn)

    def getTxnsByNym(self, nym: str):
        # TODO Implement this
        pass

    def getTxnsByType(self, txnType):
        edgeClass = getEdgeFromTxnType(txnType)
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
            TARGET_NYM: target,
            TXN_TYPE: DISCLO,
            NONCE: base58.b58encode(nonce),
            DATA: base58.b58encode(boxedMsg)
        }
        self.submit(op, identifier=origin)

    def doGetAttributeTxn(self, identifier, attrName):
        op = {
            TARGET_NYM: identifier,
            TXN_TYPE: GET_ATTR,
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

    def getAllAttributesForNym(self, nym, identifier=None):
        # TODO: Does this need to get attributes from the nodes?
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
        return attributes

    def doGetNym(self, nym, identifier=None):
        identifier = identifier if identifier else self.defaultIdentifier
        op = {
            TARGET_NYM: nym,
            TXN_TYPE: GET_NYM,
        }
        self.submit(op, identifier=identifier)

    def doGetTxn(self, txnId, identifier=None):
        identifier = identifier if identifier else self.defaultIdentifier
        op = {
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
