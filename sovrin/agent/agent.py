import json
import uuid

from typing import Dict, Any
from typing import Tuple

import asyncio

from anoncreds.protocol.issuer_key import IssuerKey
from anoncreds.protocol.proof_builder import ProofBuilder
from anoncreds.protocol.types import Credential
from anoncreds.protocol.utils import strToCharmInteger
from anoncreds.protocol.verifier import Verifier
from plenum.common.log import getlogger
from plenum.common.looper import Looper
from plenum.common.port_dispenser import genHa
from plenum.common.types import Identifier
from anoncreds.protocol.cred_def_secret_key import CredDefSecretKey
from anoncreds.protocol.issuer_secret_key import IssuerSecretKey
from anoncreds.protocol.issuer import Issuer
from sovrin.client.wallet.claim_def import ClaimDef, IssuerPubKey

from sovrin.common.identity import Identity

from plenum.common.error import fault
from plenum.common.exceptions import RemoteNotFound
from plenum.common.motor import Motor
from plenum.common.startable import Status
from plenum.common.txn import TYPE, DATA, IDENTIFIER, NONCE, NAME, VERSION, \
    ORIGIN, TARGET_NYM
from plenum.common.types import f
from plenum.common.util import getCryptonym, isHex, cryptonymToHex, \
    randomString
from sovrin.agent.agent_net import AgentNet
from sovrin.agent.msg_types import AVAIL_CLAIM_LIST, CLAIM, REQUEST_CLAIM, \
    ACCEPT_INVITE, CLAIM_PROOF, CLAIM_PROOF_STATUS
from sovrin.client.client import Client
from sovrin.client.wallet.link import Link, constant
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.txn import ATTR_NAMES, REF
from sovrin.common.util import verifySig, getConfig, getEncodedAttrs, \
    charmDictToStringDict, stringDictToCharmDict, ensureReqCompleted, \
    getCredDefIsrKeyAndExecuteCallback

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
        self._eventListeners = {}   # Dict[str, set(Callable)]
        self._name = name

        AgentNet.__init__(self,
                          name=self._name.replace(" ", ""),
                          port=port,
                          basedirpath=basedirpath,
                          msgHandler=self.handleEndpointMessage)

        # Client used to connect to Sovrin and forward on owner's txns
        self.client = client  # type: Client

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
            CLAIM: self._handleReqClaimResponse,
            ACCEPT_INVITE: self._acceptInvite,
            REQUEST_CLAIM: self._reqClaim,
            CLAIM_PROOF: self.verifyClaimProof,
            EVENT: self._eventHandler,
            CLAIM_PROOF_STATUS: self.handleClaimProofStatus
        }

    @property
    def wallet(self) -> Wallet:
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
        data = {
            CLAIMS_LIST_FIELD: claimLists
        }
        if alreadyAccepted:
            data[ALREADY_ACCEPTED_FIELD] = alreadyAccepted

        return WalletedAgent.getCommonMsg(AVAIL_CLAIM_LIST, data)

    @staticmethod
    def createClaimMsg(claim):
        return WalletedAgent.getCommonMsg(CLAIM, claim)

    def _eventHandler(self, msg):
        body, (frm, ha) = msg
        isVerified = self._isVerified(body)
        if isVerified:
            eventName = body[EVENT_NAME]
            data = body[DATA]
            self.notifyEventListeners(eventName, **data)

    def notifyEventListeners(self, eventName, **args):
        for el in self._eventListeners[eventName]:
            el(notifier=self, **args)

    def notifyMsgListener(self, msg):
        self.notifyEventListeners(EVENT_NOTIFY_MSG, msg=msg)

    def handleEndpointMessage(self, msg):
        body, frm = msg
        handler = self.msgHandlers.get(body.get(TYPE))
        if handler:
            frmHa = self.endpoint.getRemote(frm).ha
            handler((body, (frm, frmHa)))
        else:
            raise NotImplementedError

    def _handleError(self, msg):
        body, (frm, ha) = msg
        self.notifyMsgListener("Error ({}) occurred while processing this "
                             "msg: {}".format(body[DATA], body[REQ_MSG]))

    def _fetchAllAvailableClaimsInWallet(self, li, availableClaims):

        fetchedCount = 0

        def postFetchCredDef(reply, err):
            nonlocal fetchedCount
            fetchedCount += 1
            postAllFetched()

        for name, version, origin in availableClaims:
            req = self.wallet.requestClaimDef((name, version, origin),
                                              sender=self.wallet.defaultId)

            self.client.submitReqs(req)

            self.loop.call_later(.2, ensureReqCompleted, self.loop,
                                 req.reqId, self.client, postFetchCredDef)

        # TODO: Find a better name
        def postAllFetched():
            if fetchedCount == len(availableClaims):
                if availableClaims:
                    self.notifyMsgListener("    Available claims: {}".
                                         format(",".join(
                        [n for n, _, _ in availableClaims])))
                self._syncLinkPostAvailableClaimsRcvd(li, availableClaims)
        postAllFetched()

    def _handleAcceptInviteResponse(self, msg):
        body, (frm, ha) = msg
        isVerified = self._isVerified(body)
        if isVerified:
            logger.debug("got accept invite response: {}".format(body))
            identifier = body.get(IDENTIFIER)
            li = self._getLinkByTarget(getCryptonym(identifier))
            if li:
                # TODO: Show seconds took to respond
                self.notifyMsgListener("Response from {}:".format(li.name))
                self.notifyMsgListener("    Signature accepted.")
                self.notifyMsgListener("    Trust established.")
                alreadyAccepted = body[DATA].get(ALREADY_ACCEPTED_FIELD)
                if alreadyAccepted:
                    self.notifyMsgListener("    Already accepted.")
                else:
                    self.notifyMsgListener("    Identifier created in Sovrin.")

                li.linkStatus = constant.LINK_STATUS_ACCEPTED
                li.targetVerkey = constant.TARGET_VER_KEY_SAME_AS_ID
                availableClaims = []
                for cl in body[DATA][CLAIMS_LIST_FIELD]:
                    if not self.wallet.getClaimDef(seqNo=cl['claimDefSeqNo']):
                        name, version = cl[NAME], cl[VERSION]
                        availableClaims.append((name, version,
                                                li.remoteIdentifier))
                # TODO: Handle case where agent can send claims in batches.
                # So consider a scenario where first time an accept invite is
                # sent, agent sends 2 claims and the second time accept
                # invite is sent, agent sends 3 claims.
                if availableClaims:
                    li.availableClaims.extend(availableClaims)
                self._fetchAllAvailableClaimsInWallet(li, availableClaims)
            else:
                self.notifyMsgListener("No matching link found")

    def _handleReqClaimResponse(self, msg):
        body, (frm, ha) = msg
        isVerified = self._isVerified(body)
        if isVerified:
            self.notifyMsgListener("Signature accepted.")
            identifier = body.get(IDENTIFIER)
            claim = body[DATA]
            self.notifyMsgListener("Received {}.\n".format(claim[NAME]))
            li = self._getLinkByTarget(getCryptonym(identifier))
            if li:
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
            self.notifyMsgListener("Signature rejected")
        return isVerified

    def _getLinkByTarget(self, target) -> Link:
        return self.wallet.getLinkInvitationByTarget(target)

    def _syncLinkPostAvailableClaimsRcvd(self, li, availableClaims):
        self._checkIfLinkIdentifierWrittenToSovrin(li, availableClaims)

    def _checkIfLinkIdentifierWrittenToSovrin(self, li: Link,
                                              availableClaims):
        identity = Identity(identifier=li.verkey)
        req = self.wallet.requestIdentity(identity,
                                        sender=self.wallet.defaultId)
        self.client.submitReqs(req)
        self.notifyMsgListener("Synchronizing...")

        def getNymReply(reply, err, availableClaims, li: Link):
            if reply.get(DATA) and json.loads(reply[DATA])[TARGET_NYM] == li.verkey:
                self.notifyMsgListener(
                    "    Confirmed identifier written to Sovrin.")
                availableClaimNames = [n for n, _, _ in availableClaims]
                self.notifyEventListeners(EVENT_POST_ACCEPT_INVITE,
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
            version = body[VERSION]
            origin = body[ORIGIN]
            # TODO: Need to do validation
            uValue = strToCharmInteger(body['U'])
            claimDef = self.wallet.getClaimDef(key=(name, version, origin))
            attributes = self._getClaimsAttrsFor(link.nonce,
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
            self.signAndSendToCaller(resp, link.localIdentifier, frm)
        else:
            raise NotImplementedError

    def verifyClaimProof(self, msg: Any):
        body, (frm, ha) = msg
        link = self.verifyAndGetLink(msg)
        if link:
            proof = body['proof']
            encodedAttrs = body['encodedAttrs']
            # TODO: Use stringDictToCharmDict
            for iid, attrs in encodedAttrs.items():
                encodedAttrs[iid] = {n: strToCharmInteger(v) for n, v in
                                     attrs.items()}
            revealedAttrs = body['verifiableAttrs']
            nonce = int(body[NONCE], 16)
            claimDefKey = body['claimDefKey']

            def verify(reply, error):
                # TODO: Do json validation
                nonlocal proof, nonce, body
                data = json.loads(reply.get(DATA))
                pk = data.get(DATA)
                pk = stringDictToCharmDict(pk)
                pk['R'] = stringDictToCharmDict(pk['R'])
                proof = ProofBuilder.prepareProofFromDict({
                    'issuer': data[ORIGIN], 'proof': proof
                })
                ipk = {
                    data[ORIGIN]: IssuerKey(data.get(REF), **pk)
                }
                result = Verifier.verifyProof(ipk, proof, nonce,
                                              encodedAttrs,
                                              revealedAttrs)
                logger.debug("ip, proof, nonce, encoded, revealed is {} {} {} {} {}".
                             format(ipk, proof, nonce,
                                              encodedAttrs,
                                              revealedAttrs))
                logger.debug("result is {}".format(str(result)))
                resp = {
                    TYPE: CLAIM_PROOF_STATUS,
                    DATA:
                        "Your claim {} {} has been received and {}".
                            format(body[NAME], body[VERSION],
                                   "verified" if result else "not-verified"),
                }
                self.signAndSendToCaller(resp, link.localIdentifier, frm)

            getCredDefIsrKeyAndExecuteCallback(self.wallet, self.client, print,
                                               self.loop, tuple(claimDefKey),
                                               verify)

    def handleClaimProofStatus(self, msg: Any):
        body, (frm, ha) = msg
        data = body.get(DATA)
        self.notifyMsgListener(data)

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
            logger.debug("proceeding with link: {}".format(link.name))
            identifier = body.get(f.IDENTIFIER.nm)
            idy = Identity(identifier)
            try:
                pendingCount = self.wallet.addSponsoredIdentity(idy)
                logger.debug("pending request count {}".format(pendingCount))
                alreadyAdded = False
            except Exception as e:
                if e.args[0] == 'identifier already added':
                    alreadyAdded = True
                    logger.debug(
                        "link {} already accepted".format(link.name))
                else:
                    logger.warning("Exception raised while adding nym, "
                                   "error was: {}".format(e.args[0]))
                    raise e

            def sendClaimList(reply=None, error=None):
                logger.debug("sent to sovrin {}".format(identifier))
                resp = self.createAvailClaimListMsg(
                    self.getAvailableClaimList(), alreadyAccepted=alreadyAdded)
                self.signAndSendToCaller(resp, link.localIdentifier, frm)

            if alreadyAdded:
                logger.debug("already accepted, "
                             "so directly sending available claims")
                sendClaimList()
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

    def _getClaimsAttrsFor(self, nonce, attrNames):
        res = {}
        attributes = self.getAttributes(nonce)
        if attributes:
            for nm in attrNames:
                res[nm] = attributes.get(nm)
        return res

    def getAttributes(self, nonce):
        raise NotImplementedError

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

