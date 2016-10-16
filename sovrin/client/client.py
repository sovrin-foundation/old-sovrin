import json
import traceback
import uuid
from collections import deque
from typing import Dict, Union, Tuple, Optional, Callable

from base58 import b58decode, b58encode
import pyorient

from raet.raeting import AutoMode

from plenum.common.error import fault
from plenum.common.log import getlogger
from plenum.client.client import Client as PlenumClient
from plenum.server.router import Router
from plenum.common.startable import Status
from plenum.common.stacked import SimpleStack
from plenum.common.txn import REPLY, STEWARD, NAME, VERSION, REQACK, REQNACK, \
    TXN_ID, TARGET_NYM, NONCE
from plenum.common.types import OP_FIELD_NAME, f, HA
from plenum.common.util import libnacl
from plenum.persistence.orientdb_store import OrientDbStore
from sovrin.common.txn import TXN_TYPE, ATTRIB, DATA, GET_NYM, ROLE, \
    SPONSOR, NYM, GET_TXNS, LAST_TXN, TXNS, CRED_DEF, ISSUER_KEY, SKEY, DISCLO,\
    GET_ATTR
from sovrin.common.util import getConfig
from sovrin.persistence.client_req_rep_store_file import ClientReqRepStoreFile
from sovrin.persistence.client_req_rep_store_orientdb import \
    ClientReqRepStoreOrientDB
from sovrin.persistence.client_txn_log import ClientTxnLog
from sovrin.persistence.identity_graph import getEdgeByTxnType, IdentityGraph

logger = getlogger()


class Client(PlenumClient):
    def __init__(self,
                 name: str,
                 nodeReg: Dict[str, HA]=None,
                 ha: Union[HA, Tuple[str, int]]=None,
                 peerHA: Union[HA, Tuple[str, int]]=None,
                 basedirpath: str=None,
                 config=None):
        config = config or getConfig()
        super().__init__(name,
                         nodeReg,
                         ha,
                         basedirpath,
                         config)
        self.graphStore = self.getGraphStore()
        self.autoDiscloseAttributes = False
        self.requestedPendingTxns = False
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
        self._observers = {}  # type Dict[str, Callable]
        self._observerSet = set()  # makes it easier to guard against duplicates

    def handlePeerMessage(self, msg):
        """
        Use the peerMsgRouter to pass the messages to the correct
         function that handles them

        :param msg: the P2P client message.
        """
        return self.peerMsgRouter.handle(msg)

    def _getOrientDbStore(self):
        return OrientDbStore(user=self.config.OrientDB["user"],
                             password=self.config.OrientDB["password"],
                             dbName=self.name,
                             storageType=pyorient.STORAGE_TYPE_PLOCAL)

    def getReqRepStore(self):
        if self.config.ReqReplyStore == "orientdb":
            return ClientReqRepStoreOrientDB(self._getOrientDbStore())
        else:
            return ClientReqRepStoreFile(self.name, self.basedirpath)

    def getGraphStore(self):
        return IdentityGraph(self._getOrientDbStore()) if \
            self.config.ClientIdentityGraph else None

    def getTxnLogStore(self):
        return ClientTxnLog(self.name, self.basedirpath)

    def handleOneNodeMsg(self, wrappedMsg, excludeFromCli=None) -> None:
        msg, sender = wrappedMsg
        # excludeGetTxns = (msg.get(OP_FIELD_NAME) == REPLY and
        #                   msg[f.RESULT.nm].get(TXN_TYPE) == GET_TXNS)
        excludeReqAcks = msg.get(OP_FIELD_NAME) == REQACK
        excludeReqNacks = msg.get(OP_FIELD_NAME) == REQNACK
        excludeReply = msg.get(OP_FIELD_NAME) == REPLY
        excludeFromCli = excludeFromCli or excludeReqAcks or excludeReqNacks \
                         or excludeReply
        super().handleOneNodeMsg(wrappedMsg, excludeFromCli)
        if OP_FIELD_NAME not in msg:
            logger.error("Op absent in message {}".format(msg))

    def postReplyRecvd(self, reqId, frm, result, numReplies):
        reply = super().postReplyRecvd(reqId, frm, result, numReplies)
        if reply:
            for name in self._observers:
                try:
                    self._observers[name](name, reqId, frm, result, numReplies)
                except Exception as ex:
                    logger.error("Observer threw an exception", exc_info=ex)
            if isinstance(self.reqRepStore, ClientReqRepStoreOrientDB):
                self.reqRepStore.setConsensus(reqId)
            if result[TXN_TYPE] == NYM:
                if self.graphStore:
                    self.addNymToGraph(result)
            elif result[TXN_TYPE] == ATTRIB:
                if self.graphStore:
                    self.graphStore.addAttribTxnToGraph(result)
            elif result[TXN_TYPE] == GET_NYM:
                if self.graphStore:
                    if DATA in result and result[DATA]:
                        self.addNymToGraph(json.loads(result[DATA]))
            elif result[TXN_TYPE] == GET_TXNS:
                if DATA in result and result[DATA]:
                    data = json.loads(result[DATA])
                    self.reqRepStore.setLastTxnForIdentifier(
                        result[f.IDENTIFIER.nm], data[LAST_TXN])
                    if self.graphStore:
                        for txn in data[TXNS]:
                            if txn[TXN_TYPE] == NYM:
                                self.addNymToGraph(txn)
                            elif txn[TXN_TYPE] == ATTRIB:
                                try:
                                    self.graphStore.addAttribTxnToGraph(txn)
                                except pyorient.PyOrientCommandException as ex:
                                    fault(ex, "An exception was raised while "
                                              "adding attribute")

            elif result[TXN_TYPE] == CRED_DEF:
                if self.graphStore:
                    self.graphStore.addCredDefTxnToGraph(result)
            elif result[TXN_TYPE] == ISSUER_KEY:
                if self.graphStore:
                    self.graphStore.addIssuerKeyTxnToGraph(result)
            else:
                logger.debug("Unknown type {}".format(result[TXN_TYPE]))

    def requestConfirmed(self, reqId: int) -> bool:
        if isinstance(self.reqRepStore, ClientReqRepStoreOrientDB):
            return self.reqRepStore.requestConfirmed(reqId)
        else:
            return self.txnLog.hasTxnWithReqId(reqId)

    def hasConsensus(self, reqId: int) -> Optional[str]:
        if isinstance(self.reqRepStore, ClientReqRepStoreOrientDB):
            return self.reqRepStore.hasConsensus(reqId)
        else:
            return super().hasConsensus(reqId)

    def addNymToGraph(self, txn):
        origin = txn.get(f.IDENTIFIER.nm)
        if txn.get(ROLE) == SPONSOR:
            if not self.graphStore.hasSteward(origin):
                try:
                    self.graphStore.addNym(None, nym=origin, role=STEWARD)
                except pyorient.PyOrientCommandException as ex:
                    logger.trace("Error occurred adding nym to graph")
                    logger.trace(traceback.format_exc())
        self.graphStore.addNymTxnToGraph(txn)

    def getTxnById(self, txnId: str):
        if self.graphStore:
            txns = list(self.graphStore.getResultForTxnIds(txnId).values())
            return txns[0] if txns else {}
        else:
            # TODO: Add support for fetching reply by transaction id
            # serTxn = self.reqRepStore.getResultForTxnId(txnId)
            pass
        # TODO Add merkleInfo as well

    def getTxnsByNym(self, nym: str):
        raise NotImplementedError

    def getTxnsByType(self, txnType):
        if self.graphStore:
            edgeClass = getEdgeByTxnType(txnType)
            if edgeClass:
                cmd = "select from {}".format(edgeClass)
                result = self.graphStore.client.command(cmd)
                if result:
                    return [r.oRecordData for r in result]
            return []
        else:
            txns = self.txnLog.getTxnsByType(txnType)
            # TODO: Fix ASAP
            if txnType == CRED_DEF:
                for txn in txns:
                    txn[DATA] = json.loads(txn[DATA].replace("\'", '"')
                                           .replace('"{', '{')
                                           .replace('}"', '}'))
                    txn[NAME] = txn[DATA][NAME]
                    txn[VERSION] = txn[DATA][VERSION]
            return txns

    # TODO: Just for now. Remove it later
    def doAttrDisclose(self, origin, target, txnId, key):
        box = libnacl.public.Box(b58decode(origin), b58decode(target))

        data = json.dumps({TXN_ID: txnId, SKEY: key})
        nonce, boxedMsg = box.encrypt(data.encode(), pack_nonce=False)

        op = {
            TARGET_NYM: target,
            TXN_TYPE: DISCLO,
            NONCE: b58encode(nonce),
            DATA: b58encode(boxedMsg)
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

    def hasNym(self, nym):
        if self.graphStore:
            return self.graphStore.hasNym(nym)
        else:
            for txn in self.txnLog.getTxnsByType(NYM):
                if txn.get(TXN_TYPE) == NYM:
                    return True
            return False

    def _statusChanged(self, old, new):
        super()._statusChanged(old, new)

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

    def registerObserver(self, observer: Callable, name=None):
        if not name:
            name = uuid.uuid4()
        if name in self._observers or observer in self._observerSet:
            raise RuntimeError("Observer {} already registered".format(name))
        self._observers[name] = observer
        self._observerSet.add(observer)

    def deregisterObserver(self, name):
        if name not in self._observers:
            raise RuntimeError("Observer {} not registered".format(name))
        self._observerSet.remove(self._observers[name])
        del self._observers[name]

    def hasObserver(self, name):
        return name in self._observerSet
