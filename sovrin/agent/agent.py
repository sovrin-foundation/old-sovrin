import asyncio

from datetime import datetime
from typing import Dict
from typing import Tuple

import asyncio

from plenum.common.looper import Looper
from plenum.common.types import Identifier
from plenum.test.helper import genHa
from sovrin.cli.helper import ensureReqCompleted

from sovrin.common.identity import Identity

from plenum.common.error import fault
from plenum.common.exceptions import RemoteNotFound
from plenum.common.motor import Motor
from plenum.common.startable import Status
from plenum.common.txn import TYPE, DATA, IDENTIFIER, NONCE, NAME, VERSION, \
    TARGET_NYM, TXN_TYPE, NYM
from plenum.common.types import f
from plenum.common.util import getCryptonym, isHex, cryptonymToHex, getlogger, \
    randomString
from sovrin.agent.agent_net import AgentNet
from sovrin.agent.msg_types import AVAIL_CLAIM_LIST, CLAIMS, REQUEST_CLAIMS, \
    ACCEPT_INVITE, CLAIM_NAME_FIELD, EVENT_POST_ACCEPT_INVITE
from sovrin.client.client import Client
from sovrin.client.wallet.claim import AvailableClaimData, ReceivedClaim
from sovrin.client.wallet.claim import ClaimDef, ClaimDefKey
from sovrin.client.wallet.link_invitation import Link, t
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.util import verifySig

CLAIMS_LIST_FIELD = 'availableClaimsList'
CLAIMS_FIELD = 'claims'
REQ_MSG = "REQ_MSG"

ERROR = "ERROR"


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
            REQUEST_CLAIMS: self._reqClaim
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
        resp[IDENTIFIER] = self.wallet.defaultId
        signature = self.wallet.signMsg(resp, identifier)
        resp[f.SIG.nm] = signature
        self.sendMessage(resp, destName=frm)

    @staticmethod
    def getCommonMsg(type):
        msg = {}
        msg[TYPE] = type
        return msg

    @staticmethod
    def createAvailClaimListMsg(claimLists):
        msg = WalletedAgent.getCommonMsg(AVAIL_CLAIM_LIST)
        msg[CLAIMS_LIST_FIELD] = claimLists
        return msg

    @staticmethod
    def createClaimsMsg(claims):
        msg = WalletedAgent.getCommonMsg(CLAIMS)
        msg[CLAIMS_FIELD] = claims
        return msg

    def notifyObservers(self, msg):
        for o in self._observers:
            o.notify(self, msg)

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
                # Not sure how to know if the responder is a trust anchor or not
                self.notifyObservers("    Identifier created in Sovrin.")
                availableClaims = []
                for cl in body[CLAIMS_LIST_FIELD]:
                    name, version, claimDefSeqNo = \
                        cl[NAME], cl[VERSION], \
                        cl['claimDefSeqNo']
                    claimDefKey = ClaimDefKey(name, version, claimDefSeqNo)
                    availableClaims.append(AvailableClaimData(claimDefKey))

                    if cl.get('definition', None):
                        self.wallet.addClaimDef(
                            ClaimDef(claimDefKey, cl['definition']))
                    else:
                        # TODO: Go and get definition from Sovrin and store
                        # it in wallet's claim def store
                        raise NotImplementedError

                li.linkStatus = t.LINK_STATUS_ACCEPTED
                li.targetVerkey = t.TARGET_VER_KEY_SAME_AS_ID
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
            for claim in body[CLAIMS_FIELD]:
                self.notifyObservers("Received {}.".format(claim[NAME]))
                li = self._getLinkByTarget(getCryptonym(identifier))
                if li:
                    name, version, claimDefSeqNo = \
                        claim[NAME], claim[VERSION], \
                        claim['claimDefSeqNo']
                    issuerKeys = {}  # TODO: Need to decide how/where to get it
                    values = claim['values']  # TODO: Need to finalize this
                    rc = ReceivedClaim(
                        ClaimDefKey(name, version, claimDefSeqNo),
                        issuerKeys,
                        values)
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

    def notifyEventListeners(self, eventName, *args):
        for el in self._eventListeners[eventName]:
            el(*args)

    def _checkIfLinkIdentifierWrittenToSovrin(self, li: Link,
                                              availableClaims):
        identity = Identity(identifier=li.localIdentifier)
        req = self.wallet.requestIdentity(identity,
                                        sender=self.wallet.defaultId)
        # self.client.submitReqs(req)
        self.notifyObservers("Synchronizing...")

        def getNymReply(reply, err, availableClaims, li):
            self.notifyObservers("Confirmed identifier written to Sovrin.")
            self.notifyEventListeners(EVENT_POST_ACCEPT_INVITE, availableClaims)

        # self.loop.call_later(.2, ensureReqCompleted, self.loop,
        #                             req.reqId, self.client, getNymReply,
        #                             availableClaims, li)

    def _reqClaim(self, msg):
        body, (frm, ha) = msg
        link = self.verifyAndGetLink(msg)
        if link:
            claimName = body[CLAIM_NAME_FIELD]
            claimsToSend = []
            for cl in self.getClaimList():
                if cl[NAME] == claimName:
                    claimsToSend.append(cl)

            resp = self.createClaimsMsg(claimsToSend)
            self.signAndSendToCaller(resp, link.localIdentifier, frm)
        else:
            raise NotImplementedError

    def _acceptInvite(self, msg):
        body, (frm, ha) = msg
        link = self.verifyAndGetLink(msg)
        if link:
            identifier = body.get(f.IDENTIFIER.nm)
            idy = Identity(identifier)
            self.wallet.addSponsoredIdentity(idy)
            reqs = self.wallet.preparePending()

            def sendClaimList(reply, error):
                logger.debug("sent to sovrin {}".format(identifier))
                resp = self.createAvailClaimListMsg(self.getAvailableClaimList())
                self.signAndSendToCaller(resp, link.localIdentifier, frm)

            logger.debug("sending to sovrin {}".format(identifier))
            # Assuming there was only one pending request
            self._sendToSovrinAndDo(reqs[0], clbk=sendClaimList)

        # TODO: If I have the below exception thrown, somehow the
        # error msg which is sent in verifyAndGetLink is not being received
        # on the other end, so for now, commented, need to come back to this
        # else:
        #     raise NotImplementedError

    def _sendToSovrinAndDo(self, req, clbk=None, *args):
        self.client.submitReqs(req)
        loop = asyncio.get_event_loop()
        ensureReqCompleted(loop, req.reqId, self.client, clbk, *args)


def runAgent(agentClass, name, wallet=None, basedirpath=None, port=None,
             startRunning=True):
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
        with Looper(debug=True) as looper:
            looper.add(agent)
            logger.debug("Running {} now (port: {})".format(name, port))
            looper.run()
    else:
        return agent