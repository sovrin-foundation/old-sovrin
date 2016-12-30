import asyncio
import collections
import inspect
import json
import time
from abc import abstractmethod
from datetime import datetime
from typing import Dict, Union

from base58 import b58decode
from plenum.common.log import getlogger
from plenum.common.signer_did import DidSigner
from plenum.common.signing import serializeMsg
from plenum.common.txn import TYPE, DATA, NONCE, IDENTIFIER, NAME, VERSION, \
    TARGET_NYM, ATTRIBUTES, VERKEY
from plenum.common.types import f
from plenum.common.util import getTimeBasedId, getCryptonym, \
    isMaxCheckTimeExpired, convertTimeBasedReqIdToMillis
from plenum.common.verifier import DidVerifier

from anoncreds.protocol.issuer import Issuer
from anoncreds.protocol.prover import Prover
from anoncreds.protocol.verifier import Verifier
from sovrin.agent.agent_issuer import AgentIssuer
from sovrin.agent.agent_prover import AgentProver
from sovrin.agent.agent_verifier import AgentVerifier
from sovrin.agent.constants import ALREADY_ACCEPTED_FIELD, CLAIMS_LIST_FIELD, \
    REQ_MSG, PING, ERROR, EVENT, EVENT_NAME, EVENT_NOTIFY_MSG, \
    EVENT_POST_ACCEPT_INVITE, PONG
from sovrin.agent.exception import NonceNotFound, SignatureRejected
from sovrin.agent.msg_constants import ACCEPT_INVITE, REQUEST_CLAIM, \
    CLAIM_PROOF, \
    AVAIL_CLAIM_LIST, CLAIM, CLAIM_PROOF_STATUS, NEW_AVAILABLE_CLAIMS, \
    REF_REQUEST_ID
from sovrin.client.wallet.attribute import Attribute, LedgerStore
from sovrin.client.wallet.link import Link, constant, ClaimProofRequest
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.exceptions import LinkNotFound, LinkAlreadyExists, \
    NotConnectedToNetwork, LinkNotReady
from sovrin.common.identity import Identity
from sovrin.common.txn import ENDPOINT
from sovrin.common.util import ensureReqCompleted

logger = getlogger()


class Walleted(AgentIssuer, AgentProver, AgentVerifier):
    """
    An agent with a self-contained wallet.

    Normally, other logic acts upon a remote agent. That other logic holds keys
    and signs messages and transactions that the Agent then forwards. In this
    case, the agent holds a wallet.
    """

    def __init__(self,
                 issuer: Issuer = None,
                 prover: Prover = None,
                 verifier: Verifier = None):

        AgentIssuer.__init__(self, issuer)
        AgentProver.__init__(self, prover)
        AgentVerifier.__init__(self, verifier)

        # TODO Why are we syncing the client here?
        if self.client:
            self.syncClient()
        self.rcvdMsgStore = {}  # type: Dict[reqId, [reqMsg]]
        self.msgHandlers = {
            ERROR: self._handleError,
            EVENT: self._eventHandler,

            PING: self._handlePing,
            ACCEPT_INVITE: self._handleAcceptance,

            REQUEST_CLAIM: self.processReqClaim,
            CLAIM: self.handleReqClaimResponse,

            CLAIM_PROOF: self.verifyClaimProof,
            CLAIM_PROOF_STATUS: self.handleProofStatusResponse,

            PONG: self._handlePong,
            AVAIL_CLAIM_LIST: self._handleAcceptInviteResponse,

            NEW_AVAILABLE_CLAIMS: self._handleNewAvailableClaimsDataResponse
        }

    def syncClient(self):
        obs = self._wallet.handleIncomingReply
        if not self.client.hasObserver(obs):
            self.client.registerObserver(obs)
        self._wallet.pendSyncRequests()
        prepared = self._wallet.preparePending()
        self.client.submitReqs(*prepared)

    @property
    def wallet(self) -> Wallet:
        return self._wallet

    @wallet.setter
    def wallet(self, wallet):
        self._wallet = wallet

    @property
    def lockedMsgs(self):
        # Msgs for which signature verification is required
        return ACCEPT_INVITE, REQUEST_CLAIM, CLAIM_PROOF, \
               CLAIM, AVAIL_CLAIM_LIST, EVENT, PONG

    async def postClaimVerif(self, claimName, link, frm):
        raise NotImplementedError

    def isClaimAvailable(self, link, claimName):
        raise NotImplementedError

    async def _postClaimVerif(self, claimName, link, frm):
        link.verifiedClaimProofs.append(claimName)
        await self.postClaimVerif(claimName, link, frm)

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
        self.signAndSend(msg=self.getErrorResponse(reqBody, respMsg),
                         signingIdr=self.wallet.defaultId, toRaetStackName=to)

    # TODO: Verification needs to be moved out of it,
    # use `verifySignature` instead
    def verifyAndGetLink(self, msg):
        body, (frm, ha) = msg
        # key = body.get(f.IDENTIFIER.nm)
        #
        # signature = body.get(f.SIG.nm)
        # verified = verifySig(key, signature, body)
        # if not self.verifySignature(body):
        #     self.logAndSendErrorResp(frm, body, "Signature Rejected",
        #                              "Signature verification failed for msg: {}"
        #                              .format(str(msg)))
        #     return None

        nonce = body.get(NONCE)
        try:
            return self.linkFromNonce(nonce,
                                      remoteIdr=body.get(f.IDENTIFIER.nm),
                                      remoteHa=ha)
        except NonceNotFound:
            self.logAndSendErrorResp(frm, body,
                                     "Nonce not found",
                                     "Nonce not found for msg: {}".format(msg))
            return None

    def linkFromNonce(self, nonce, remoteIdr, remoteHa):
        internalId = self.getInternalIdByInvitedNonce(nonce)
        link = self.wallet.getLinkByInternalId(internalId)
        if not link:
            # QUESTION: We use wallet.defaultId as the local identifier,
            # this looks ok for test code, but not production code
            link = Link(str(internalId),
                        self.wallet.defaultId,
                        invitationNonce=nonce,
                        remoteIdentifier=remoteIdr,
                        remoteEndPoint=remoteHa,
                        internalId=internalId)
            self.wallet.addLink(link)
        else:
            link.remoteIdentifier = remoteIdr
            link.remoteEndPoint = remoteHa
        return link

    @abstractmethod
    def getInternalIdByInvitedNonce(self, nonce):
        raise NotImplementedError

    def signAndSend(self, msg, signingIdr=None, toRaetStackName=None,
                    linkName=None, origReqId=None):
        if linkName:
            assert not (signingIdr or toRaetStackName)
            self.connectTo(linkName)
            link = self.wallet.getLink(linkName, required=True)
            ha = link.getRemoteEndpoint(required=True)

            # TODO ensure status is appropriate with code like the following
            # if link.linkStatus != constant.LINK_STATUS_ACCEPTED:
            #     raise LinkNotReady('link status is {}'.format(link.linkStatus))

            if not link.localIdentifier:
                raise LinkNotReady('local identifier not set up yet')
            signingIdr = link.localIdentifier
            params = dict(ha=ha)
        else:
            params = dict(name=toRaetStackName)
        # origReqId needs to be supplied when you want to respond to request
        # so that on receiving end, response can be matched with request
        # if origReqId:
        #     msg[f.REQ_ID.nm] = origReqId
        # else:
        #     msg[f.REQ_ID.nm] = getTimeBasedId()
        msg[f.REQ_ID.nm] = getTimeBasedId()
        if origReqId:
            msg[REF_REQUEST_ID] = origReqId

        msg[IDENTIFIER] = signingIdr
        signature = self.wallet.signMsg(msg, signingIdr)
        msg[f.SIG.nm] = signature
        self.sendMessage(msg, **params)
        return msg[f.REQ_ID.nm]

    @staticmethod
    def getCommonMsg(typ, data):
        msg = {
            TYPE: typ,
            DATA: data
        }
        return msg

    @classmethod
    def createAvailClaimListMsg(cls, claimLists, alreadyAccepted=False):
        data = {
            CLAIMS_LIST_FIELD: claimLists
        }
        if alreadyAccepted:
            data[ALREADY_ACCEPTED_FIELD] = alreadyAccepted

        return cls.getCommonMsg(AVAIL_CLAIM_LIST, data)

    @classmethod
    def createNewAvailableClaimsMsg(cls, claimLists):
        data = {
            CLAIMS_LIST_FIELD: claimLists
        }
        return cls.getCommonMsg(NEW_AVAILABLE_CLAIMS, data)

    @classmethod
    def createClaimMsg(cls, claim):
        return cls.getCommonMsg(CLAIM, claim)

    def _eventHandler(self, msg):
        body, _ = msg
        eventName = body[EVENT_NAME]
        data = body[DATA]
        self.notifyEventListeners(eventName, **data)

    def notifyEventListeners(self, eventName, **data):
        for el in self._eventListeners.get(eventName, []):
            el(notifier=self, **data)

    def notifyMsgListener(self, msg):
        self.notifyEventListeners(EVENT_NOTIFY_MSG, msg=msg)

    def isSignatureVerifRespRequired(self, typ):
        return typ in self.lockedMsgs and typ not in [EVENT, PING, PONG]

    def sendSigVerifResponseMsg(self, respMsg, to, reqMsgTyp, identifier):
        if self.isSignatureVerifRespRequired(reqMsgTyp):
            self.notifyToRemoteCaller(EVENT_NOTIFY_MSG,
                                      respMsg, identifier, to)

    def handleEndpointMessage(self, msg):
        body, frm = msg
        logger.debug("Message received (from -> {}): {}".format(frm, body))
        for reqFieldName in (TYPE, f.REQ_ID.nm):
            reqFieldValue = body.get(reqFieldName)
            if not reqFieldValue:
                errorMsg = "{} not specified in message: {}".format(
                    reqFieldName, body)
                self.notifyToRemoteCaller(EVENT_NOTIFY_MSG,
                                          errorMsg, self.wallet.defaultId, frm)
                logger.warn("{}".format(errorMsg))
                return

        typ = body.get(TYPE)
        link = self.wallet.getLinkInvitationByTarget(body.get(f.IDENTIFIER.nm))

        # If accept invite is coming the first time, then use the default
        # identifier of the wallet since link wont be created
        if typ == ACCEPT_INVITE and link is None:
            localIdr = self.wallet.defaultId
        else:
            localIdr = link.localIdentifier

        if typ in self.lockedMsgs:
            try:
                self.verifySignature(body)
            except SignatureRejected:
                self.sendSigVerifResponseMsg("\nSignature rejected.",
                                             frm, typ, localIdr)
                return
        reqId = body.get(f.REQ_ID.nm)

        oldResps = self.rcvdMsgStore.get(reqId)
        if oldResps:
            oldResps.append(msg)
        else:
            self.rcvdMsgStore[reqId] = [msg]

        # TODO: Question: Should we sending an acknowledgement for every message?
        # We are sending, ACKs for "signature accepted" messages too
        self.sendSigVerifResponseMsg("\nSignature accepted.",
                                     frm, typ, localIdr)

        handler = self.msgHandlers.get(typ)
        if handler:
            # TODO we should verify signature here
            frmHa = self.endpoint.getRemote(frm).ha
            res = handler((body, (frm, frmHa)))
            if inspect.isawaitable(res):
                self.loop.call_soon(asyncio.ensure_future, res)
        else:
            raise NotImplementedError("No type handle found for {} message".
                                      format(typ))

    def _handleError(self, msg):
        body, _ = msg
        self.notifyMsgListener("Error ({}) occurred while processing this "
                               "msg: {}".format(body[DATA], body[REQ_MSG]))

    def _handlePing(self, msg):
        body, (frm, ha) = msg
        link = self.wallet.getLinkByNonce(body.get(NONCE))
        if link:
            self.signAndSend({TYPE: 'pong'}, self.wallet.defaultId, frm,
                             origReqId=body.get(f.REQ_ID.nm))

    def _handlePong(self, msg):
        body, (frm, ha) = msg
        identifier = body.get(IDENTIFIER)
        li = self._getLinkByTarget(getCryptonym(identifier))
        if li:
            self.notifyMsgListener("    Pong received.")
        else:
            self.notifyMsgListener("    Pong received from unknown endpoint")

    def _handleNewAvailableClaimsDataResponse(self, msg):
        body, _ = msg
        isVerified = self.verifySignature(body)
        if isVerified:
            identifier = body.get(IDENTIFIER)
            li = self._getLinkByTarget(getCryptonym(identifier))
            if li:
                self.notifyResponseFromMsg(li.name, body.get(f.REQ_ID.nm))

                rcvdAvailableClaims = body[DATA][CLAIMS_LIST_FIELD]
                newAvailableClaims = self._getNewAvailableClaims(
                    li, rcvdAvailableClaims)
                if newAvailableClaims:
                    li.availableClaims.extend(newAvailableClaims)
                    claimNames = ", ".join(
                        [n for n, _, _ in newAvailableClaims])
                    self.notifyMsgListener(
                        "    Available Claim(s): {}\n".format(claimNames))

            else:
                self.notifyMsgListener("No matching link found")

    @staticmethod
    def _getNewAvailableClaims(li, rcvdAvailableClaims):
        return [(cl[NAME], cl[VERSION], li.remoteIdentifier) for cl in
                rcvdAvailableClaims]

    def _handleAcceptInviteResponse(self, msg):
        body, _ = msg
        identifier = body.get(IDENTIFIER)
        li = self._getLinkByTarget(getCryptonym(identifier))
        if li:
            # TODO: Show seconds took to respond
            self.notifyResponseFromMsg(li.name, body.get(f.REQ_ID.nm))
            self.notifyMsgListener("    Trust established.")
            alreadyAccepted = body[DATA].get(ALREADY_ACCEPTED_FIELD)
            if alreadyAccepted:
                self.notifyMsgListener("    Already accepted.")
            else:
                self.notifyMsgListener("    Identifier created in Sovrin.")

                li.linkStatus = constant.LINK_STATUS_ACCEPTED
                # li.targetVerkey = constant.TARGET_VER_KEY_SAME_AS_ID

                rcvdAvailableClaims = body[DATA][CLAIMS_LIST_FIELD]
                newAvailableClaims = self._getNewAvailableClaims(
                    li, rcvdAvailableClaims)
                if newAvailableClaims:
                    li.availableClaims.extend(newAvailableClaims)
                    self.notifyMsgListener("    Available Claim(s): {}".
                        format(",".join(
                        [n for n, _, _ in newAvailableClaims])))

                self._checkIfLinkIdentifierWrittenToSovrin(li,
                                                           newAvailableClaims)

        else:
            self.notifyMsgListener("No matching link found")

    def getVerkeyForLink(self, link):
        # TODO: Get latest verkey for this link's remote identifier from Sovrin
        if link.targetVerkey:
            return link.targetVerkey
        else:
            raise Exception("verkey not set in link")

    def getLinkForMsg(self, msg):
        nonce = msg.get(NONCE)
        link = self.wallet.getLinkByNonce(nonce)
        if link:
            return link
        else:
            raise LinkNotFound

    def verifySignature(self, msg: Dict[str, str]):
        signature = msg.get(f.SIG.nm)
        identifier = msg.get(IDENTIFIER)
        msgWithoutSig = {k: v for k, v in msg.items() if k != f.SIG.nm}
        # TODO This assumes the current key is the cryptonym. This is a BAD
        # ASSUMPTION!!! Sovrin needs to provide the current key.
        ser = serializeMsg(msgWithoutSig)
        signature = b58decode(signature.encode())
        typ = msg.get(TYPE)
        # TODO: Maybe keeping ACCEPT_INVITE open is a better option than keeping
        # an if condition here?
        if typ == ACCEPT_INVITE:
            verkey = msg.get(VERKEY)
        else:
            try:
                link = self.getLinkForMsg(msg)
                verkey = self.getVerkeyForLink(link)
            except LinkNotFound:
                # This is for verification of `NOTIFY` events
                link = self.wallet.getLinkInvitationByTarget(identifier)
                # TODO: If verkey is None, it should be fetched from Sovrin.
                # Assuming CID for now.
                verkey = link.targetVerkey

        v = DidVerifier(verkey, identifier=identifier)
        if not v.verify(signature, ser):
            raise SignatureRejected
        else:
            return True

    def _getLinkByTarget(self, target) -> Link:
        return self.wallet.getLinkInvitationByTarget(target)

    def _checkIfLinkIdentifierWrittenToSovrin(self, li: Link, availableClaims):
        req = self.getIdentity(li.localIdentifier)
        self.notifyMsgListener("\nSynchronizing...")

        def getNymReply(reply, err, availableClaims, li: Link):
            if reply.get(DATA) and json.loads(reply[DATA])[TARGET_NYM] == \
                    li.localIdentifier:
                self.notifyMsgListener(
                    "    Confirmed identifier written to Sovrin.")
                availableClaimNames = [n for n, _, _ in availableClaims]
                self.notifyEventListeners(
                    EVENT_POST_ACCEPT_INVITE,
                    availableClaimNames=availableClaimNames,
                    claimProofReqsCount=len(li.claimProofRequests))
            else:
                self.notifyMsgListener(
                    "    Identifier is not yet written to Sovrin")

        self.loop.call_later(.2, ensureReqCompleted, self.loop, req.key,
                             self.client, getNymReply, (availableClaims, li))

    def notifyResponseFromMsg(self, linkName, reqId=None):
        if reqId:
            # TODO: This logic assumes that the req id is time based
            curTimeBasedId = getTimeBasedId()
            timeTakenInMillis = convertTimeBasedReqIdToMillis(
                curTimeBasedId - reqId)

            if timeTakenInMillis >= 1000:
                responseTime = ' ({} sec)'.format(
                    round(timeTakenInMillis / 1000, 2))
            else:
                responseTime = ' ({} ms)'.format(round(timeTakenInMillis, 2))
        else:
            responseTime = ''

        self.notifyMsgListener("\nResponse from {}{}:".format(linkName,
                                                              responseTime))

    def notifyToRemoteCaller(self, event, msg, signingIdr, to, origReqId=None):
        resp = {
            TYPE: EVENT,
            EVENT_NAME: event,
            DATA: {'msg': msg}
        }
        self.signAndSend(resp, signingIdr, to, origReqId=origReqId)

    def _handleAcceptance(self, msg):
        body, (frm, ha) = msg
        link = self.verifyAndGetLink(msg)
        # TODO this is really kludgy code... needs refactoring
        # exception handling, separation of concerns, etc.
        if not link:
            return
        logger.debug("proceeding with link: {}".format(link.name))
        identifier = body.get(f.IDENTIFIER.nm)
        verkey = body.get(VERKEY)
        idy = Identity(identifier, verkey=verkey)
        link.targetVerkey = verkey
        try:
            pendingCount = self.wallet.addSponsoredIdentity(idy)
            logger.debug("pending request count {}".format(pendingCount))
            alreadyAdded = False
        except Exception as e:
            if e.args[0] in ['identifier already added']:
                alreadyAdded = True
            else:
                logger.warning("Exception raised while adding nym, "
                               "error was: {}".format(e.args[0]))
                raise e

        def sendClaimList(reply=None, error=None):
            logger.debug("sent to sovrin {}".format(identifier))
            resp = self.createAvailClaimListMsg(
                self.getAvailableClaimList(), alreadyAccepted=alreadyAdded)
            self.signAndSend(resp, link.localIdentifier, frm,
                             origReqId=body.get(f.REQ_ID.nm))

        if alreadyAdded:
            sendClaimList()
            logger.debug("already accepted, "
                         "so directly sending available claims")
            # self.notifyToRemoteCaller(EVENT_NOTIFY_MSG,
            #                       "    Already accepted",
            #                       link.verkey, frm)
        else:
            logger.debug(
                "not added to the ledger, so add nym to the ledger "
                "and then will send available claims")
            reqs = self.wallet.preparePending()
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
        ensureReqCompleted(self.loop, req.key, self.client, clbk, *args)

    def newAvailableClaimsPostClaimVerif(self, claimName):
        raise NotImplementedError

    def sendNewAvailableClaimsData(self, nac, frm, link):
        if len(nac) > 0:
            resp = self.createNewAvailableClaimsMsg(nac)
            self.signAndSend(resp, link.localIdentifier, frm)

    def sendPing(self, linkName):
        link = self.wallet.getLink(linkName, required=True)
        self.connectTo(linkName)
        ha = link.getRemoteEndpoint(required=True)
        params = dict(ha=ha)
        msg = {
            TYPE: 'ping',
            NONCE: link.invitationNonce,
            f.REQ_ID.nm: getTimeBasedId(),
            f.IDENTIFIER.nm: link.localIdentifier
        }
        reqId = self.sendMessage(msg, **params)

        self.notifyMsgListener("    Ping sent.")
        return reqId

    def connectTo(self, linkName):
        link = self.wallet.getLink(linkName, required=True)
        ha = link.getRemoteEndpoint(required=True)
        self.connectToHa(ha)

    def loadInvitation(self, invitationData):
        linkInvitation = invitationData["link-invitation"]
        remoteIdentifier = linkInvitation[f.IDENTIFIER.nm]
        signature = invitationData["sig"]
        linkInvitationName = linkInvitation[NAME]
        remoteEndPoint = linkInvitation.get("endpoint", None)
        linkNonce = linkInvitation[NONCE]
        claimProofRequestsJson = invitationData.get("claim-requests", None)

        claimProofRequests = []
        if claimProofRequestsJson:
            for cr in claimProofRequestsJson:
                claimProofRequests.append(
                    ClaimProofRequest(cr[NAME], cr[VERSION], cr[ATTRIBUTES],
                                      cr['verifiableAttributes']))

        self.notifyMsgListener("1 link invitation found for {}.".
                               format(linkInvitationName))

        self.notifyMsgListener("Creating Link for {}.".
                               format(linkInvitationName))
        self.notifyMsgListener("Generating Identifier and Signing key.")
        # TODO: Would we always have a trust anchor corresponding ot a link?

        li = Link(name=linkInvitationName,
                  trustAnchor=linkInvitationName,
                  remoteIdentifier=remoteIdentifier,
                  remoteEndPoint=remoteEndPoint,
                  invitationNonce=linkNonce,
                  claimProofRequests=claimProofRequests)

        self.wallet.addLink(li)
        return li

    def loadInvitationFile(self, filePath):
        with open(filePath) as data_file:
            invitationData = json.load(
                data_file, object_pairs_hook=collections.OrderedDict)
            linkInvitation = invitationData.get("link-invitation")
            if not linkInvitation:
                raise LinkNotFound
            linkName = linkInvitation["name"]
            existingLinkInvites = self.wallet. \
                getMatchingLinks(linkName)
            if len(existingLinkInvites) >= 1:
                raise LinkAlreadyExists
            Link.validate(invitationData)
            link = self.loadInvitation(invitationData)
            return link

    def acceptInvitation(self, link: Union[str, Link]):
        if isinstance(link, str):
            link = self.wallet.getLink(link, required=True)
        elif isinstance(link, Link):
            pass
        else:
            raise TypeError("Type of link must be either string or Link but "
                            "provided {}".format(type(link)))
        # TODO should move to wallet in a method like accept(link)
        if not link.localIdentifier:
            signer = DidSigner()
            self.wallet.addIdentifier(signer=signer)
            link.localIdentifier = signer.identifier
        msg = {
            TYPE: ACCEPT_INVITE,
            # TODO should not send this... because origin should be the sender
            NONCE: link.invitationNonce,
            VERKEY: self.wallet.getVerkey(link.localIdentifier)
        }
        logger.debug("{} accepting invitation from {} with id {}".
                     format(self.name, link.name, link.localIdentifier))
        self.signAndSend(msg, None, None, link.name)

    def _handleSyncResp(self, link, additionalCallback):
        def _(reply, err):
            if err:
                raise RuntimeError(err)
            reqId = self._updateLinkWithLatestInfo(link, reply)
            if reqId:
                self.loop.call_later(.2,
                                     self.executeWhenResponseRcvd,
                                     time.time(), 8000,
                                     self.loop, reqId, PONG, True,
                                     additionalCallback, reply, err)
            else:
                additionalCallback(reply, err)

        return _

    def _updateLinkWithLatestInfo(self, link: Link, reply):

        if DATA in reply and reply[DATA]:
            data = json.loads(reply[DATA])
            ip, port = data.get(ENDPOINT).split(":")
            link.remoteEndPoint = (ip, int(port))

        link.linkLastSynced = datetime.now()
        self.notifyMsgListener("    Link {} synced".format(link.name))
        # TODO need to move this to after acceptance,
        # unless we want to support an anonymous ping
        # if link.remoteEndPoint:
        #     reqId = self._pingToEndpoint(link.name, link.remoteEndPoint)
        #     return reqId

    def _pingToEndpoint(self, name, endpoint):
        self.notifyMsgListener("\nPinging target endpoint: {}".
                               format(endpoint))
        reqId = self.sendPing(linkName=name)
        return reqId

    def sync(self, linkName, doneCallback=None):
        if not self.client.isReady():
            raise NotConnectedToNetwork
        link = self.wallet.getLink(linkName, required=True)
        nym = getCryptonym(link.remoteIdentifier)
        attrib = Attribute(name=ENDPOINT,
                           value=None,
                           dest=nym,
                           ledgerStore=LedgerStore.RAW)
        req = self.wallet.requestAttribute(attrib, sender=self.wallet.defaultId)
        self.client.submitReqs(req)

        if doneCallback:
            self.loop.call_later(.2,
                                 ensureReqCompleted,
                                 self.loop,
                                 req.key,
                                 self.client,
                                 self._handleSyncResp(link, doneCallback))

    def executeWhenResponseRcvd(self, startTime, maxCheckForMillis,
                                loop, reqId, respType,
                                checkIfLinkExists, clbk, *args):

        if isMaxCheckTimeExpired(startTime, maxCheckForMillis):
            clbk(None, "No response received within specified time ({} mills). "
                       "Retry the command and see if that works.\n".
                 format(maxCheckForMillis))
        else:
            found = False
            rcvdResponses = self.rcvdMsgStore.get(reqId)
            if rcvdResponses:
                for msg in rcvdResponses:
                    body, frm = msg
                    if body.get(TYPE) == respType:
                        if checkIfLinkExists:
                            identifier = body.get(IDENTIFIER)
                            li = self._getLinkByTarget(getCryptonym(identifier))
                            linkCheckOk = li is not None
                        else:
                            linkCheckOk = True

                        if linkCheckOk:
                            found = True
                            break

            if found:
                clbk(*args)
            else:
                loop.call_later(.2, self.executeWhenResponseRcvd,
                                startTime, maxCheckForMillis, loop,
                                reqId, respType, checkIfLinkExists, clbk, *args)
