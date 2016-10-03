import asyncio
import uuid

from datetime import datetime
from typing import Dict
from typing import Tuple

import asyncio

from plenum.common.log import getlogger
from plenum.common.looper import Looper
from plenum.common.port_dispenser import genHa
from plenum.common.types import Identifier
from anoncreds.protocol.cred_def_secret_key import CredDefSecretKey
from anoncreds.protocol.issuer_secret_key import IssuerSecretKey
from sovrin.cli.helper import ensureReqCompleted
from sovrin.client.wallet.cred_def import CredDef, IssuerPubKey

from sovrin.common.identity import Identity

from plenum.common.error import fault
from plenum.common.exceptions import RemoteNotFound
from plenum.common.motor import Motor
from plenum.common.startable import Status
from plenum.common.txn import TYPE, DATA, IDENTIFIER, NONCE, NAME, VERSION
from plenum.common.types import f
from plenum.common.util import getCryptonym, isHex, cryptonymToHex, \
    randomString
from sovrin.agent.agent_net import AgentNet
from sovrin.agent.msg_types import AVAIL_CLAIM_LIST, CLAIMS, REQUEST_CLAIM, \
    ACCEPT_INVITE, REQUEST_CLAIM_ATTRS, CLAIM_ATTRS
from sovrin.client.client import Client
from sovrin.client.wallet.claim import AvailableClaimData, ReceivedClaim
from sovrin.client.wallet.claim import ClaimDef, ClaimDefKey
from sovrin.client.wallet.link import Link, constant
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.txn import ATTR_NAMES
from sovrin.common.util import verifySig, getConfig

ALREADY_ACCEPTED_FIELD = 'alreadyAccepted'
CLAIMS_LIST_FIELD = 'availableClaimsList'
CLAIMS_FIELD = 'claims'
REQ_MSG = "REQ_MSG"

ERROR = "error"
EVENT = "event"
EVENT_NAME = "eventName"

EVENT_NOTIFY_MSG = "NOTIFY"
EVENT_POST_ACCEPT_INVITE = "POST_ACCEPT_INVITE_EVENT"

logger = getlogger()


class Agent(Motor, AgentNet):
    def __init__(self,
                 name: str,
                 basedirpath: str,
                 client: Client=None,
                 port: int=None):
        Motor.__init__(self)
        self._observers = set()
        self._eventListeners = {}   # Dict[str, set(Callable)]
        self._name = name

        AgentNet.__init__(self,
                          name=self._name.replace(" ", ""),
                          port=port,
                          basedirpath=basedirpath,
                          msgHandler=self.handleEndpointMessage)

        # Client used to connect to Sovrin and forward on owner's txns
        self.client = client

        # known identifiers of this agent's owner
        self.ownerIdentifiers = {}  # type: Dict[Identifier, Identity]

    def name(self):
        pass

    async def prod(self, limit) -> int:
        c = 0
        if self.get_status() == Status.starting:
            self.status = Status.started
            c += 1
        if self.client:
            c += await self.client.prod(limit)
        if self.endpoint:
            c += await self.endpoint.service(limit)
        return c

    def start(self, loop):
        super().start(loop)
        if self.client:
            self.client.start(loop)
        if self.endpoint:
            self.endpoint.start()

    def _statusChanged(self, old, new):
        pass

    def onStopping(self, *args, **kwargs):
        pass

    def connect(self, network: str):
        """
        Uses the client to connect to Sovrin
        :param network: (test|live)
        :return:
        """
        raise NotImplementedError

    def syncKeys(self):
        """
        Iterates through ownerIdentifiers and ensures the keys are correct
        according to Sovrin. Updates the updated
        :return:
        """
        raise NotImplementedError

    def handleOwnerRequest(self, request):
        """
        Consumes an owner request, verifies it's authentic (by checking against
        synced owner identifiers' keys), and handles it.
        :param request:
        :return:
        """
        raise NotImplementedError

    def handleEndpointMessage(self, msg):
        raise NotImplementedError

    def sendMessage(self, msg, destName: str=None, destHa: Tuple=None):
        try:
            remote = self.endpoint.getRemote(name=destName, ha=destHa)
        except RemoteNotFound as ex:
            fault(ex, "Do not know {} {}".format(destName, destHa))
            return
        self.endpoint.transmit(msg, remote.uid)

    def connectTo(self, ha):
        self.endpoint.connectTo(ha)

    def registerEventListener(self, eventName, listener):
        cur = self._eventListeners.get(eventName)
        if cur:
            self._eventListeners[eventName] = cur.add(listener)
        else:
            self._eventListeners[eventName] = {listener}

    def deregisterEventListener(self, eventName, listener):
        cur = self._eventListeners.get(eventName)
        if cur:
            self._eventListeners[eventName] = cur - set(listener)

    def registerObserver(self, observer):
        self._observers.add(observer)

    def deregisterObserver(self, observer):
        self._observers.remove(observer)


class WalletedAgent(Agent):
    """
    An agent with a self-contained wallet.

    Normally, other logic acts upon a remote agent. That other logic holds keys
    and signs messages and transactions that the Agent then forwards. In this
    case, the agent holds a wallet.
    """

    def __init__(self,
                 name: str,
                 basedirpath: str,
                 client: Client=None,
                 wallet: Wallet=None,
                 port: int=None):
        super().__init__(name, basedirpath, client, port)
        self._wallet = wallet or Wallet(name)
        obs = self._wallet.handleIncomingReply
        if not self.client.hasObserver(obs):
            self.client.registerObserver(obs)
        self._wallet.pendSyncRequests()
        prepared = self._wallet.preparePending()
        self.client.submitReqs(*prepared)
        self.loop = asyncio.get_event_loop()
        self.msgHandlers = {
            ERROR: self._handleError,
            AVAIL_CLAIM_LIST: self._handleAcceptInviteResponse,
            CLAIMS: self._handleReqClaimResponse,
            ACCEPT_INVITE: self._acceptInvite,
            REQUEST_CLAIM_ATTRS: self._returnClaimAttrs,
            REQUEST_CLAIM: self._reqClaim,
            CLAIM_ATTRS: self._handleClaimAttrs,
            EVENT: self._eventHandler
        }

    @property
    def wallet(self):
        return self._wallet

    @wallet.setter
    def wallet(self, wallet):
        self._wallet = wallet

    def getClaimList(self, claimNames=None):
        raise NotImplementedError

    def getAvailableClaimList(self):
        raise NotImplementedError

    def getErrorResponse(self, reqBody, errorMsg="Error"):
        invalidSigResp = {
            TYPE: ERROR,
            DATA: errorMsg,
            REQ_MSG: reqBody,

        }
        return invalidSigResp

    def logAndSendErrorResp(self, to, reqBody, respMsg, logMsg):
        logger.warning(logMsg)
        self.signAndSendToCaller(resp=self.getErrorResponse(reqBody, respMsg),
                                 identifier=self.wallet.defaultId, frm=to)

    def verifyAndGetLink(self, msg):
        body, (frm, ha) = msg
        key = body.get(f.IDENTIFIER.nm)
        signature = body.get(f.SIG.nm)
        verified = verifySig(key, signature, body)

        nonce = body.get(NONCE)
        matchingLink = self.wallet.getLinkByNonce(nonce)

        if not verified:
            self.logAndSendErrorResp(frm, body, "Signature Rejected",
                                     "Signature verification failed for msg: {}"
                                     .format(str(msg)))
            return None

        if not matchingLink:
            self.logAndSendErrorResp(frm, body, "No Such Link found",
                                     "Link not found for msg: {}".format(msg))
            return None

        matchingLink.remoteIdentifier = body.get(f.IDENTIFIER.nm)
        matchingLink.remoteEndPoint = ha
        return matchingLink

    def signAndSendToCaller(self, resp, identifier, frm):
        resp[IDENTIFIER] = identifier
        signature = self.wallet.signMsg(resp, identifier)
        resp[f.SIG.nm] = signature
        self.sendMessage(resp, destName=frm)

    @staticmethod
    def getCommonMsg(typ, data):
        msg = {
            TYPE: typ,
            DATA: data
        }
        return msg

    @staticmethod
    def createAvailClaimListMsg(claimLists, alreadyAccepted=False):
        data = {}
        data[CLAIMS_LIST_FIELD] = claimLists
        if alreadyAccepted:
            data[ALREADY_ACCEPTED_FIELD] = alreadyAccepted

        return WalletedAgent.getCommonMsg(AVAIL_CLAIM_LIST, data)

    @staticmethod
    def createClaimsAttrsMsg(claim):
        return WalletedAgent.getCommonMsg(CLAIM_ATTRS, claim)

    @staticmethod
    def createClaimsMsg(claim):
        # TODO: Should be called CLAIM_FILED, no plural
        data = {
            CLAIMS_FIELD: claim
        }
        return WalletedAgent.getCommonMsg(CLAIMS, data)

    def _eventHandler(self, msg):
        body, (frm, ha) = msg
        isVerified = self._isVerified(body)
        if isVerified:
            eventName = body[EVENT_NAME]
            data = body[DATA]
            if eventName == EVENT_NOTIFY_MSG:
                self.notifyObservers(data)
            else:
                self.notifyEventListeners(eventName, **data)

    def notifyObservers(self, msg):
        for o in self._observers:
            o.notify(self, msg)

    def notifyEventListeners(self, eventName, **args):
        for el in self._eventListeners[eventName]:
            el(**args)

    def handleEndpointMessage(self, msg):
        body, frm = msg
        handler = self.msgHandlers.get(body.get(TYPE))
        if handler:
            frmHa = self.endpoint.getRemote(frm).ha
            handler((body, (frm, frmHa)))
        else:
            raise NotImplementedError
            # logger.warning("no handler found for type {}".format(typ))

    def _handleError(self, msg):
        body, (frm, ha) = msg
        self.notifyObservers("Error ({}) occurred while processing this "
                             "msg: {}".format(body[DATA], body[REQ_MSG]))

    def _handleAcceptInviteResponse(self, msg):
        body, (frm, ha) = msg
        isVerified = self._isVerified(body)
        if isVerified:
            identifier = body.get(IDENTIFIER)
            li = self._getLinkByTarget(getCryptonym(identifier))
            if li:
                # TODO: Show seconds took to respond
                self.notifyObservers("Response from {}:".format(li.name))
                self.notifyObservers("    Signature accepted.")
                self.notifyObservers("    Trust established.")
                alreadyAccepted = body[DATA].get(ALREADY_ACCEPTED_FIELD)
                if alreadyAccepted:
                    self.notifyObservers("    Already accepted.")
                else:
                    self.notifyObservers("    Identifier created in Sovrin.")
                availableClaims = []
                for cl in body[DATA][CLAIMS_LIST_FIELD]:
                    name, version, claimDefSeqNo = cl[NAME], cl[VERSION], \
                                                   cl['claimDefSeqNo']
                    claimDefKey = ClaimDefKey(name, version, claimDefSeqNo,
                                              li.remoteIdentifier)
                    availableClaims.append(AvailableClaimData(claimDefKey))

                    if cl.get('definition', None):
                        self.wallet.addClaimDef(
                            ClaimDef(claimDefKey, cl['definition']))
                    else:
                        # TODO: Go and get definition from Sovrin and store
                        # it in wallet's claim def store
                        raise NotImplementedError

                li.linkStatus = constant.LINK_STATUS_ACCEPTED
                li.targetVerkey = constant.TARGET_VER_KEY_SAME_AS_ID
                li.updateAvailableClaims(availableClaims)

                self.wallet.addLinkInvitation(li)

                if len(availableClaims) > 0:
                    self.notifyObservers("    Available claims: {}".
                                         format(",".join([cl.claimDefKey.name
                                                          for cl in availableClaims])))
                    self._syncLinkPostAvailableClaimsRcvd(li, availableClaims)
            else:
                self.notifyObservers("No matching link found")

    def _handleRequestClaimResponse(self, msg):
        body, (frm, ha) = msg
        isVerified = self._isVerified(body)
        if isVerified:
            raise NotImplementedError

    def _handleReqClaimResponse(self, msg):
        body, (frm, ha) = msg
        isVerified = self._isVerified(body)
        if isVerified:
            self.notifyObservers("Signature accepted.")
            identifier = body.get(IDENTIFIER)
            claim = body[DATA][CLAIMS_FIELD]
            # for claim in body[CLAIMS_FIELD]:
            self.notifyObservers("Received {}.".format(claim[NAME]))
            li = self._getLinkByTarget(getCryptonym(identifier))
            if li:
                name, version, claimDefSeqNo, idr = \
                    claim[NAME], claim[VERSION], \
                    claim['claimDefSeqNo'], claim[f.IDENTIFIER.nm]
                issuerKeys = {}  # TODO: Need to decide how/where to get it
                attributes = claim['attributes']  # TODO: Need to finalize this
                rc = ReceivedClaim(
                    ClaimDefKey(name, version, claimDefSeqNo, idr),
                    issuerKeys,
                    attributes)
                rc.dateOfIssue = datetime.now()
                li.updateReceivedClaims([rc])
                self.wallet.addLinkInvitation(li)
            else:
                self.notifyObservers("No matching link found")

    def _isVerified(self, msg: Dict[str, str]):
        signature = msg.get(f.SIG.nm)
        identifier = msg.get(IDENTIFIER)
        msgWithoutSig = {}
        for k, v in msg.items():
            if k != f.SIG.nm:
                msgWithoutSig[k] = v

        key = cryptonymToHex(identifier) if not isHex(
            identifier) else identifier
        isVerified = verifySig(key, signature, msgWithoutSig)
        if not isVerified:
            self.notifyObservers("Signature rejected")
        return isVerified

    def _getLinkByTarget(self, target) -> Link:
        return self.wallet.getLinkInvitationByTarget(target)

    def _syncLinkPostAvailableClaimsRcvd(self, li, availableClaims):
        self._checkIfLinkIdentifierWrittenToSovrin(li, availableClaims)

    def _checkIfLinkIdentifierWrittenToSovrin(self, li: Link,
                                              availableClaims):
        identity = Identity(identifier=li.localIdentifier)
        req = self.wallet.requestIdentity(identity,
                                        sender=self.wallet.defaultId)
        # self.client.submitReqs(req)
        # self.notifyObservers("Synchronizing...")

        def getNymReply(reply, err, availableClaims, li):
            self.notifyObservers("Confirmed identifier written to Sovrin.")
            self.notifyEventListeners(EVENT_POST_ACCEPT_INVITE, availableClaims)

        # self.loop.call_later(.2, ensureReqCompleted, self.loop,
        #                             req.reqId, self.client, getNymReply,
        #                             availableClaims, li)

    def _reqClaim(self, msg):
        pass

    def _handleClaimAttrs(self, msg):
        body, (frm, ha) = msg
        isVerified = self._isVerified(body)
        if isVerified:
            self.notifyObservers("Signature accepted.")
            identifier = body.get(IDENTIFIER)
            claim = body[DATA]
            # for claim in body[CLAIMS_FIELD]:
            self.notifyObservers("Received {}.".format(claim[NAME]))
            li = self._getLinkByTarget(getCryptonym(identifier))
            if li:
                name, version, claimDefSeqNo, idr = \
                    claim[NAME], claim[VERSION], \
                    claim['claimDefSeqNo'], claim[f.IDENTIFIER.nm]
                issuerKeys = {}  # TODO: Need to decide how/where to get it
                attributes = claim['attributes']  # TODO: Need to finalize this
                rc = ReceivedClaim(
                    ClaimDefKey(name, version, claimDefSeqNo, idr),
                    issuerKeys,
                    attributes)
                rc.dateOfIssue = datetime.now()
                li.updateReceivedClaims([rc])
                self.wallet.addLinkInvitation(li)
            else:
                self.notifyObservers("No matching link found")

    def _returnClaimAttrs(self, msg):
        body, (frm, ha) = msg
        link = self.verifyAndGetLink(msg)
        if link:
            claimDefSeqNo = body["claimDefSeqNo"]
            claimDef = self.wallet.getCredDef(seqNo=claimDefSeqNo)
            attributes = self._getClaimsAttrsFor(link.nonce,
                                                 claimDef.attrNames)
            claimDetails = {
                NAME: claimDef.name,
                VERSION: claimDef.version,
                'attributes': attributes,
                'claimDefSeqNo': claimDefSeqNo,
                f.IDENTIFIER.nm: claimDef.origin
            }
            # # TODO: Need to have u value from alice and generate credential

            resp = self.createClaimsAttrsMsg(claimDetails)
            self.signAndSendToCaller(resp, link.localIdentifier, frm)
        else:
            raise NotImplementedError

    def notifyToRemoteCaller(self, event, msg, identifier, frm):
        resp = {
            TYPE: EVENT,
            EVENT_NAME: event,
            DATA: msg
        }
        self.signAndSendToCaller(resp, identifier, frm)

    def _acceptInvite(self, msg):
        body, (frm, ha) = msg
        link = self.verifyAndGetLink(msg)
        if link:
            identifier = body.get(f.IDENTIFIER.nm)
            idy = Identity(identifier)
            try:
                pendingCount = self.wallet.addSponsoredIdentity(idy)
                logger.debug("pending request count {}".format(pendingCount))
                alreadyAdded = False
            except Exception as e:
                if e.args[0] == 'identifier already added':
                    alreadyAdded = True
                else:
                    raise e

            def sendClaimList(reply=None, error=None):
                logger.debug("sent to sovrin {}".format(identifier))
                resp = self.createAvailClaimListMsg(
                    self.getAvailableClaimList())
                self.signAndSendToCaller(resp, link.localIdentifier, frm)

            if alreadyAdded:
                sendClaimList()
                self.notifyToRemoteCaller(EVENT_NOTIFY_MSG,
                                          "    Already accepted",
                                          link.verkey, frm)
            else:
                reqs = self.wallet.preparePending()
                logger.debug("pending requests {}".format(reqs))
                # Assuming there was only one pending request
                logger.debug("sending to sovrin {}".format(reqs[0]))
                self._sendToSovrinAndDo(reqs[0], clbk=sendClaimList)

        # TODO: If I have the below exception thrown, somehow the
        # error msg which is sent in verifyAndGetLink is not being received
        # on the other end, so for now, commented, need to come back to this
        # else:
        #     raise NotImplementedError

    def _sendToSovrinAndDo(self, req, clbk=None, *args):
        self.client.submitReqs(req)
        ensureReqCompleted(self.loop, req.reqId, self.client, clbk, *args)

    def _getClaimsAttrsFor(self, nonce, attrNames):
        res = {}
        attributes = self.getAttributes(nonce)
        if attributes:
            for nm in attrNames:
                res[nm] = attributes.get(nm)
        return res

    def addClaimDefs(self, name, version, attrNames,
                             staticPrime, credDefSeqNo, issuerKeySeqNo):
        csk = CredDefSecretKey(*staticPrime)
        sid = self.wallet.addCredDefSk(str(csk))
        # Need to modify the claim definition. We do not support types yet
        claimDef = {
            NAME: name,
            VERSION: version,
            TYPE: "CL",
            ATTR_NAMES: attrNames
        }
        wallet = self.wallet
        credDef = CredDef(seqNo=credDefSeqNo,
                          attrNames=claimDef[ATTR_NAMES],
                          name=claimDef[NAME],
                          version=claimDef[VERSION],
                          origin=wallet.defaultId,
                          typ=claimDef[TYPE],
                          secretKey=sid)
        wallet._credDefs[(name, version, wallet.defaultId)] = credDef
        isk = IssuerSecretKey(credDef, csk, uid=str(uuid.uuid4()))
        self.wallet.addIssuerSecretKey(isk)
        ipk = IssuerPubKey(N=isk.PK.N, R=isk.PK.R, S=isk.PK.S, Z=isk.PK.Z,
                           claimDefSeqNo=credDef.seqNo,
                           secretKeyUid=isk.uid, origin=wallet.defaultId,
                           seqNo=issuerKeySeqNo)
        key = (wallet.defaultId, credDefSeqNo)
        wallet._issuerPks[key] = ipk


def runAgent(agentClass, name, wallet=None, basedirpath=None, port=None,
             startRunning=True, bootstrap=False):
    config = getConfig()

    if not wallet:
        wallet = Wallet(name)
    if not basedirpath:
        basedirpath = config.baseDir
    if not port:
        _, port = genHa()

    _, clientPort = genHa()
    client = Client(randomString(6),
                    ha=("0.0.0.0", clientPort),
                    basedirpath=basedirpath)

    agent = agentClass(basedirpath=basedirpath,
                       client=client,
                       wallet=wallet,
                       port=port)
    if startRunning:
        if bootstrap:
            agent.bootstrap()
        with Looper(debug=True) as looper:
            looper.add(agent)
            logger.debug("Running {} now (port: {})".format(name, port))
            looper.run()
    else:
        return agent

