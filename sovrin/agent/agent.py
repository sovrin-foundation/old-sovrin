import asyncio
import collections
import json
import uuid
from abc import abstractmethod
from datetime import datetime
from typing import Dict, Any
from typing import Tuple

from anoncreds.protocol.cred_def_secret_key import CredDefSecretKey
from anoncreds.protocol.issuer import Issuer
from anoncreds.protocol.issuer_secret_key import IssuerSecretKey
from anoncreds.protocol.proof_builder import ProofBuilder
from anoncreds.protocol.types import Credential
from anoncreds.protocol.utils import strToCharmInteger
from anoncreds.protocol.verifier import Verifier
from plenum.common.error import fault
from plenum.common.exceptions import RemoteNotFound
from plenum.common.log import getlogger
from plenum.common.looper import Looper
from plenum.common.motor import Motor
from plenum.common.port_dispenser import genHa
from plenum.common.signer_simple import SimpleSigner
from plenum.common.startable import Status
from plenum.common.txn import TYPE, DATA, IDENTIFIER, NONCE, NAME, VERSION, \
    ORIGIN, TARGET_NYM, ATTRIBUTES
from plenum.common.types import f
from plenum.common.util import getCryptonym, randomString, getTimeBasedId
from sovrin.agent.agent_net import AgentNet
from sovrin.agent.exception import NonceNotFound, SignatureRejected
from sovrin.agent.msg_types import AVAIL_CLAIM_LIST, CLAIM, REQUEST_CLAIM, \
    ACCEPT_INVITE, CLAIM_PROOF, CLAIM_PROOF_STATUS, NEW_AVAILABLE_CLAIMS
from sovrin.client.client import Client
from sovrin.client.wallet.attribute import LedgerStore, Attribute
from sovrin.client.wallet.claim import ClaimProofRequest
from sovrin.client.wallet.claim_def import ClaimDef, IssuerPubKey
from sovrin.client.wallet.link import Link, constant
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.exceptions import LinkAlreadyExists, \
    LinkNotFound, NotConnectedToNetwork
from sovrin.common.identity import Identity
from sovrin.common.txn import ATTR_NAMES, ENDPOINT
from sovrin.common.util import verifySig, getConfig, getEncodedAttrs, \
    stringDictToCharmDict, ensureReqCompleted, \
    getCredDefIsrKeyAndExecuteCallback

ALREADY_ACCEPTED_FIELD = 'alreadyAccepted'
CLAIMS_LIST_FIELD = 'availableClaimsList'
CLAIMS_FIELD = 'claims'
REQ_MSG = "REQ_MSG"

PING = "ping"
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
        self._eventListeners = {}   # Dict[str, set(Callable)]
        self._name = name

        AgentNet.__init__(self,
                          name=self._name.replace(" ", ""),
                          port=port,
                          basedirpath=basedirpath,
                          msgHandler=self.handleEndpointMessage)

        # Client used to connect to Sovrin and forward on owner's txns
        self._client = client  # type: Client

        # known identifiers of this agent's owner
        self.ownerIdentifiers = {}  # type: Dict[Identifier, Identity]

    @property
    def client(self):
        return self._client

    @client.setter
    def client(self, client):
        self._client = client

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

    def connectToHa(self, ha):
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
        if self.client:
            self.syncClient()
        self.loop = asyncio.get_event_loop()
        self.msgHandlers = {
            ERROR: self._handleError,
            EVENT: self._eventHandler,

            PING: self._handlePing,
            ACCEPT_INVITE: self._acceptInvite,
            REQUEST_CLAIM: self._reqClaim,
            CLAIM_PROOF: self.verifyClaimProof,

            AVAIL_CLAIM_LIST: self._handleAcceptInviteResponse,
            CLAIM: self._handleReqClaimResponse,
            CLAIM_PROOF_STATUS: self.handleClaimProofStatus,
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
               CLAIM, AVAIL_CLAIM_LIST, EVENT

    def postClaimVerif(self, claimName, link, frm):
        raise NotImplementedError

    def isClaimAvailable(self, link, claimName):
        raise NotImplementedError

    def _postClaimVerif(self, claimName, link, frm):
        link.verifiedClaimProofs.append(claimName)
        self.postClaimVerif(claimName, link, frm)

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

    def verifyAndGetLink(self, msg):
        body, (frm, ha) = msg
        key = body.get(f.IDENTIFIER.nm)

        signature = body.get(f.SIG.nm)
        verified = verifySig(key, signature, body)
        if not verified:
            self.logAndSendErrorResp(frm, body, "Signature Rejected",
                                     "Signature verification failed for msg: {}"
                                     .format(str(msg)))
            return None

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

    def signAndSend(self, msg, signingIdr, toRaetStackName,
                    linkName=None, origReqId=None):
        if linkName:
            assert not signingIdr
            assert not toRaetStackName
            self.connectTo(linkName)
            link = self.wallet.getLink(linkName, required=True)
            ha = link.getRemoteEndpoint(required=True)
            signingIdr = self.wallet._requiredIdr(link.localIdentifier)
            params = dict(destHa=ha)
        else:
            params = dict(destName=toRaetStackName)

        if origReqId:
            msg[f.REQ_ID.nm] = origReqId
        else:
            msg[f.REQ_ID.nm] = getTimeBasedId()

        msg[IDENTIFIER] = signingIdr
        signature = self.wallet.signMsg(msg, signingIdr)
        msg[f.SIG.nm] = signature
        self.sendMessage(msg, **params)

    @staticmethod
    def getCommonMsg(typ, data):
        msg = {
            TYPE: typ,
            DATA: data
        }
        return msg

    @staticmethod
    def createAvailClaimListMsg(claimLists, alreadyAccepted=False):
        data = {
            CLAIMS_LIST_FIELD: claimLists
        }
        if alreadyAccepted:
            data[ALREADY_ACCEPTED_FIELD] = alreadyAccepted

        return WalletedAgent.getCommonMsg(AVAIL_CLAIM_LIST, data)

    @staticmethod
    def createNewAvailableClaimsMsg(claimLists):
        data = {
            CLAIMS_LIST_FIELD: claimLists
        }
        return WalletedAgent.getCommonMsg(NEW_AVAILABLE_CLAIMS, data)


    @staticmethod
    def createClaimMsg(claim):
        return WalletedAgent.getCommonMsg(CLAIM, claim)

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
        return typ in self.lockedMsgs and typ not in [EVENT]

    def sendSigVerifResponseMsg(self, respMsg, to, reqMsgTyp):
        if self.isSignatureVerifRespRequired(reqMsgTyp):
            self.notifyToRemoteCaller(EVENT_NOTIFY_MSG,
                                      respMsg, self.wallet.defaultId, to)

    def handleEndpointMessage(self, msg):
        body, frm = msg
        typ = body.get(TYPE)
        if typ in self.lockedMsgs:
            try:
                self._isVerified(body)
            except SignatureRejected:
                self.sendSigVerifResponseMsg("\nSignature rejected.",
                                             frm, typ)
                return
        self.sendSigVerifResponseMsg("\nSignature accepted.", frm, typ)

        handler = self.msgHandlers.get(typ)
        if handler:
            # TODO we should verify signature here
            frmHa = self.endpoint.getRemote(frm).ha
            handler((body, (frm, frmHa)))
        else:
            raise NotImplementedError("No type handle found for {} message".
                                      format(typ))

    def _handleError(self, msg):
        body, _ = msg
        self.notifyMsgListener("Error ({}) occurred while processing this "
                               "msg: {}".format(body[DATA], body[REQ_MSG]))

    def _sendGetClaimDefRequests(self, availableClaims, postFetchCredDef=None):
        for name, version, origin in availableClaims:
            req = self.wallet.requestClaimDef((name, version, origin),
                                              sender=self.wallet.defaultId)

            self.client.submitReqs(req)

            if postFetchCredDef:
                self.loop.call_later(.2, ensureReqCompleted, self.loop,
                                 req.reqId, self.client, postFetchCredDef)

    def _handlePing(self, msg):
        body, (frm, ha) = msg
        link = self.verifyAndGetLink(msg)
        # TODO instead of asserting, have previous throw exception
        assert link
        self.notifyMsgListener("Ping received. Sending Pong.")
        self.signAndSend({'msg': 'pong'}, link.localIdentifier, frm,
                         origReqId=body.get(f.REQ_ID.nm))

    def _handlePong(self, msg):
        body, _ = msg
        link = self.verifyAndGetLink(msg)
        # TODO instead of asserting, have previous throw exception
        assert link
        self.notifyMsgListener("Pong received.")

    def _fetchAllAvailableClaimsInWallet(self, li, newAvailableClaims,
                                         postAllFetched):

        fetchedCount = 0

        def postEachCredDefFetch(reply, err):
            nonlocal fetchedCount
            fetchedCount += 1
            postAllCreDefFetched()

        self._sendGetClaimDefRequests(newAvailableClaims, postEachCredDefFetch)

        # TODO: Find a better name
        def postAllCreDefFetched():
            if fetchedCount == len(newAvailableClaims):
                postAllFetched(li, newAvailableClaims)

        postAllCreDefFetched()

    def _handleNewAvailableClaimsDataResponse(self, msg):
        body, _ = msg
        isVerified = self._isVerified(body)
        if isVerified:
            identifier = body.get(IDENTIFIER)
            li = self._getLinkByTarget(getCryptonym(identifier))
            if li:
                self.notifyResponseFromMsg(li.name, body.get(f.REQ_ID.nm))

                def postAllFetched(li, newAvailableClaims):
                    if newAvailableClaims:
                        claimNames = ", ".join(
                            [n for n, _, _ in newAvailableClaims])
                        self.notifyMsgListener(
                            "    Available claims: {}\n".format(claimNames))

                self._processNewAvailableClaimsData(
                    li, body[DATA][CLAIMS_LIST_FIELD], postAllFetched)
            else:
                self.notifyMsgListener("No matching link found")

    def _getNewAvailableClaims(self, li, rcvdAvailableClaims):
        availableClaims = []
        for cl in rcvdAvailableClaims:
            if not self.wallet.getClaimDef(seqNo=cl['claimDefSeqNo']):
                name, version = cl[NAME], cl[VERSION]
                availableClaims.append((name, version,
                                        li.remoteIdentifier))

        return availableClaims

    def _processNewAvailableClaimsData(self, li, rcvdAvailableClaims,
                                       postAllFetched):
        newAvailableClaims = self._getNewAvailableClaims(
            li, rcvdAvailableClaims)

        # TODO: Handle case where agent can send claims in batches.
        # So consider a scenario where first time an accept invite is
        # sent, agent sends 2 claims and the second time accept
        # invite is sent, agent sends 3 claims.
        if newAvailableClaims:
            li.availableClaims.extend(newAvailableClaims)

        self._fetchAllAvailableClaimsInWallet(li, newAvailableClaims,
                                              postAllFetched)

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
                li.targetVerkey = constant.TARGET_VER_KEY_SAME_AS_ID
                self._processNewAvailableClaimsData(
                    li, body[DATA][CLAIMS_LIST_FIELD],
                    self._syncLinkPostAvailableClaimsRcvd)
        else:
            self.notifyMsgListener("No matching link found")

    def _handleReqClaimResponse(self, msg):
        body, _ = msg
        identifier = body.get(IDENTIFIER)
        claim = body[DATA]
        li = self._getLinkByTarget(getCryptonym(identifier))
        if li:
            self.notifyResponseFromMsg(li.name, body.get(f.REQ_ID.nm))
            self.notifyMsgListener('    Received claim "{}".\n'.format(
                claim[NAME]))
            name, version, idr = \
                claim[NAME], claim[VERSION], claim[f.IDENTIFIER.nm]
            attributes = claim['attributes']
            self.wallet.addAttrFrom(idr, attributes)
            data = body['data']
            credential = Credential(*(strToCharmInteger(x) for x in
                                      [data['A'], data['e'],
                                       data['vprimeprime']]))

            self.wallet.addCredentialToProofBuilder((data[NAME], data[VERSION],
                                              data[f.IDENTIFIER.nm]),
                                             data[f.IDENTIFIER.nm],
                                             credential)
        else:
            self.notifyMsgListener("No matching link found")

    @staticmethod
    def _isVerified(msg: Dict[str, str]):
        signature = msg.get(f.SIG.nm)
        identifier = msg.get(IDENTIFIER)
        msgWithoutSig = {k: v for k, v in msg.items() if k != f.SIG.nm}
        # TODO This assumes the current key is the cryptonym. This is a BAD
        # ASSUMPTION!!! Sovrin needs to provide the current key.
        if not verifySig(identifier, signature, msgWithoutSig):
            raise SignatureRejected
        else:
            return True

    def _getLinkByTarget(self, target) -> Link:
        return self.wallet.getLinkInvitationByTarget(target)

    def _syncLinkPostAvailableClaimsRcvd(self, li, newAvailableClaims):
        if newAvailableClaims:
            self.notifyMsgListener("    Available claims: {}".
                format(",".join(
                [n for n, _, _ in newAvailableClaims])))
        self._checkIfLinkIdentifierWrittenToSovrin(li, newAvailableClaims)

    def _checkIfLinkIdentifierWrittenToSovrin(self, li: Link,
                                              availableClaims):
        identity = Identity(identifier=li.verkey)
        req = self.wallet.requestIdentity(identity,
                                        sender=self.wallet.defaultId)
        self.client.submitReqs(req)
        self.notifyMsgListener("\nSynchronizing...")

        def getNymReply(reply, err, availableClaims, li: Link):
            if reply.get(DATA) and json.loads(reply[DATA])[TARGET_NYM] == \
                    li.verkey:
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

        self.loop.call_later(.2, ensureReqCompleted, self.loop, req.reqId,
                             self.client, getNymReply, (availableClaims, li))

    def _reqClaim(self, msg):
        body, (frm, ha) = msg
        link = self.verifyAndGetLink(msg)
        if link:
            name = body[NAME]
            if not self.isClaimAvailable(link, name):
                self.notifyToRemoteCaller(
                    EVENT_NOTIFY_MSG, "This claim is not yet available",
                    self.wallet.defaultId, frm, origReqId=body.get(f.REQ_ID.nm))
                return

            version = body[VERSION]
            origin = body[ORIGIN]
            # TODO: Need to do validation
            uValue = strToCharmInteger(body['U'])
            claimDef = self.wallet.getClaimDef(key=(name, version, origin))
            attributes = self._getClaimsAttrsFor(link.internalId,
                                                 claimDef.attrNames)
            encodedAttrs = next(iter(getEncodedAttrs(link.verkey,
                                                attributes).values()))
            sk = CredDefSecretKey.fromStr(
                self.wallet.getClaimDefSk(claimDef.secretKey))
            pk = self.wallet.getIssuerPublicKeyForClaimDef(claimDef.seqNo)
            cred = Issuer.generateCredential(uValue, encodedAttrs, pk, sk)
            claimDetails = {
                NAME: claimDef.name,
                VERSION: claimDef.version,
                'attributes': attributes,
                # TODO: the name should not be identifier but origin
                f.IDENTIFIER.nm: claimDef.origin,
                'A': str(cred[0]),
                'e': str(cred[1]),
                'vprimeprime': str(cred[2])
            }
            resp = self.createClaimMsg(claimDetails)
            self.signAndSend(resp, link.localIdentifier, frm,
                             origReqId=body.get(f.REQ_ID.nm))
        else:
            raise NotImplementedError

    def verifyClaimProof(self, msg: Any):
        body, (frm, ha) = msg
        link = self.verifyAndGetLink(msg)
        if link:
            proof = body['proof']
            encodedAttrs = body['encodedAttrs']
            for iid, attrs in encodedAttrs.items():
                encodedAttrs[iid] = stringDictToCharmDict(attrs)
            revealedAttrs = body['verifiableAttrs']
            nonce = int(body[NONCE], 16)
            # Converting from list to tuple
            claimDefKey = tuple((body['claimDefKey']))

            def verify(r, e, name, version, origin):
                # This assumes that author of claimDef is same as the author of
                # issuerPublicKey
                # TODO: Do json validation
                nonlocal proof, nonce, body
                claimDefKey = name, version, origin
                claimDef = self.wallet.getClaimDef(key=claimDefKey)
                issuerKey = self.wallet.getIssuerPublicKeyForClaimDef(
                    claimDef.seqNo)
                proof = ProofBuilder.prepareProofFromDict({
                    'issuer': origin, 'proof': proof
                })
                claimName = body[NAME]
                ipk = {
                    origin: issuerKey
                }
                result = Verifier.verifyProof(ipk, proof, nonce,
                                              encodedAttrs,
                                              revealedAttrs)
                logger.info("claim {} verification result: {}".
                            format(claimName, result))

                # TODO: Following line is temporary and need to be removed
                # result = True

                logger.debug("ip, proof, nonce, encoded, revealed is "
                             "{} {} {} {} {}".
                             format(ipk, proof, nonce,
                                              encodedAttrs,
                                              revealedAttrs))
                logger.debug("result is {}".format(str(result)))
                resp = {
                    TYPE: CLAIM_PROOF_STATUS,
                    DATA:
                        '    Your claim {} {} has been received '
                        'and {}verified\n'.
                            format(body[NAME], body[VERSION],
                                   '' if result else 'is not yet '),
                }
                self.signAndSend(resp, link.localIdentifier, frm,
                                 origReqId=body.get(f.REQ_ID.nm))

                if result:
                    self._postClaimVerif(claimName, link, frm)

            getCredDefIsrKeyAndExecuteCallback(self.wallet, self.client, print,
                                               self.loop, claimDefKey,
                                               verify, pargs=claimDefKey)

    def notifyResponseFromMsg(self, linkName, reqId=None):
        if reqId:
            # TODO: This logic assumes that the req id is time based
            timeTakenInMillis = (getTimeBasedId() - reqId)/1000

            if timeTakenInMillis >= 1000:
                responseTime = ' ({} sec)'.format(round(timeTakenInMillis/1000, 2))
            else:
                responseTime = ' ({} ms)'.format(round(timeTakenInMillis, 2))
        else:
            responseTime = ''

        self.notifyMsgListener("\nResponse from {}{}:".format(linkName,
                                                              responseTime))

    def handleClaimProofStatus(self, msg: Any):
        body, _ = msg
        data = body.get(DATA)
        identifier = body.get(IDENTIFIER)
        li = self._getLinkByTarget(getCryptonym(identifier))
        self.notifyResponseFromMsg(li.name, body.get(f.REQ_ID.nm))
        self.notifyMsgListener(data)

    def notifyToRemoteCaller(self, event, msg, signingIdr, frm, origReqId=None):
        resp = {
            TYPE: EVENT,
            EVENT_NAME: event,
            DATA: {'msg': msg}
        }
        self.signAndSend(resp, signingIdr, frm, origReqId=origReqId)

    def _acceptInvite(self, msg):
        body, (frm, ha) = msg
        link = self.verifyAndGetLink(msg)
        # TODO this is really kludgy code... needs refactoring
        # exception handling, separation of concerns, etc.
        if not link:
            return
        logger.debug("proceeding with link: {}".format(link.name))
        identifier = body.get(f.IDENTIFIER.nm)
        idy = Identity(identifier)
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
                "not accepted, so add nym to sovrin "
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
        ensureReqCompleted(self.loop, req.reqId, self.client, clbk, *args)

    def _getClaimsAttrsFor(self, internalId, attrNames):
        res = {}
        attributes = self.getAttributes(internalId)
        if attributes:
            for nm in attrNames:
                res[nm] = attributes.get(nm)
        return res

    def getAttributes(self, nonce):
        raise NotImplementedError

    def newAvailableClaimsPostClaimVerif(self, claimName):
        raise NotImplementedError

    def sendNewAvailableClaimsData(self, nac, frm, link):
        if len(nac) > 0:
            resp = self.createNewAvailableClaimsMsg(nac)
            self.signAndSend(resp, link.localIdentifier, frm)

    def addClaimDefs(self, name, version, attrNames,
                             staticPrime, credDefSeqNo, issuerKeySeqNo):
        csk = CredDefSecretKey(*staticPrime)
        sid = self.wallet.addClaimDefSk(str(csk))
        # Need to modify the claim definition. We do not support types yet
        claimDef = {
            NAME: name,
            VERSION: version,
            TYPE: "CL",
            ATTR_NAMES: attrNames
        }
        wallet = self.wallet
        claimDef = ClaimDef(seqNo=credDefSeqNo,
                           attrNames=claimDef[ATTR_NAMES],
                           name=claimDef[NAME],
                           version=claimDef[VERSION],
                           origin=wallet.defaultId,
                           typ=claimDef[TYPE],
                           secretKey=sid)
        wallet._claimDefs[(name, version, wallet.defaultId)] = claimDef
        isk = IssuerSecretKey(claimDef, csk, uid=str(uuid.uuid4()))
        self.wallet.addIssuerSecretKey(isk)
        ipk = IssuerPubKey(N=isk.PK.N, R=isk.PK.R, S=isk.PK.S, Z=isk.PK.Z,
                           claimDefSeqNo=claimDef.seqNo,
                           secretKeyUid=isk.uid, origin=wallet.defaultId,
                           seqNo=issuerKeySeqNo)
        key = (wallet.defaultId, credDefSeqNo)
        wallet._issuerPks[key] = ipk

    def sendPing(self, linkName):
        self.signAndSend({'msg': PING}, None, None, linkName)
        self.notifyMsgListener("Ping sent.")

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
                    ClaimProofRequest(cr[NAME], cr[VERSION], cr[ATTRIBUTES]))

        self.notifyMsgListener("1 link invitation found for {}.".
                               format(linkInvitationName))
        # TODO: Assuming it is cryptographic identifier
        alias = "cid-" + str(len(self.wallet.identifiers) + 1)
        signer = SimpleSigner(alias=alias)
        self.wallet.addSigner(signer=signer)

        self.notifyMsgListener("Creating Link for {}.".
                               format(linkInvitationName))
        self.notifyMsgListener("Generating Identifier and Signing key.")
        # TODO: Would we always have a trust anchor corresponding ot a link?
        trustAnchor = linkInvitationName
        li = Link(linkInvitationName,
                  signer.alias + ":" + signer.identifier,
                  trustAnchor, remoteIdentifier,
                  remoteEndPoint, linkNonce,
                  claimProofRequests, invitationData=invitationData)
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
            existingLinkInvites = self.wallet.\
                getMatchingLinks(linkName)
            if len(existingLinkInvites) >= 1:
                raise LinkAlreadyExists
            Link.validate(invitationData)
            link = self.loadInvitation(invitationData)
            return link

    def acceptInvitation(self, linkName):
        link = self.wallet.getLink(linkName, required=True)
        idr = self.wallet._requiredIdr(link.localIdentifier)
        msg = {
            TYPE: ACCEPT_INVITE,
            f.IDENTIFIER.nm: idr,
            NONCE: link.invitationNonce,
        }
        self.signAndSend(msg, None, None, linkName)

    def _handleSyncResp(self, link, additionalCallback):
        def _(reply, err):
            if err:
                raise RuntimeError(err)
            self._updateLinkWithLatestInfo(link, reply)
            additionalCallback(reply, err)
        return _

    def _updateLinkWithLatestInfo(self, link: Link, reply):

        if DATA in reply and reply[DATA]:
            data = json.loads(reply[DATA])
            ip, port = data.get(ENDPOINT).split(":")
            link.remoteEndPoint = (ip, int(port))

        link.linkLastSynced = datetime.now()
        self.notifyMsgListener("    Link {} synced".format(link.name))
        if link.remoteEndPoint:
            self._pingToEndpoint(link.remoteEndPoint)

    def _pingToEndpoint(self, endPoint):
        self.notifyMsgListener("    Pinging target endpoint: {}".format(endPoint))
        self.notifyMsgListener("        [Not Yet Implemented]")
        # TODO implement ping

    def sync(self, linkName, doneCallback=None):
        if not self.client.isReady():
            raise NotConnectedToNetwork
        link = self.wallet.getLink(linkName, required=True)
        nym = getCryptonym(link.remoteIdentifier)
        attrib = Attribute(name=ENDPOINT,
                           value=None,
                           dest=nym,
                           ledgerStore=LedgerStore.RAW)
        req = self.wallet.requestAttribute(
            attrib, sender=self.wallet.defaultId)
        self.client.submitReqs(req)

        if doneCallback:
            self.loop.call_later(.2,
                                 ensureReqCompleted,
                                 self.loop,
                                 req.reqId,
                                 self.client,
                                 self._handleSyncResp(link, doneCallback))


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

