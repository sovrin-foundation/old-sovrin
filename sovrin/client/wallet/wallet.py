import json

import datetime
import operator

from collections import deque
from typing import Dict
from typing import Optional

from ledger.util import F
from plenum.client.wallet import Wallet as PWallet
from plenum.common.txn import TXN_TYPE, TARGET_NYM, DATA, \
    IDENTIFIER, NAME, VERSION, IP, PORT, KEYS, TYPE, NYM, STEWARD, ROLE, RAW
from plenum.common.types import Identifier, f
from sovrin.client.wallet.attribute import Attribute, AttributeKey
from sovrin.client.wallet.claim import ClaimDefKey, ClaimDef
from sovrin.client.wallet.cred_def import CredDefKey, CredDef, CredDefSk
from sovrin.client.wallet.credential import Credential
# from sovrin.client.wallet.link import Link
from sovrin.client.wallet.link_invitation import Link
from sovrin.common.txn import ATTRIB, GET_TXNS, GET_ATTR, CRED_DEF, GET_CRED_DEF, \
    GET_NYM, SPONSOR
from sovrin.common.identity import Identity
from sovrin.common.types import Request

ENCODING = "utf-8"


class Sponsoring:
    """
    Mixin to add sponsoring behaviors to a Wallet
    """
    def __init__(self):
        self._sponsored = {}  # type: Dict[Identifier, Identity]

    def addSponsoredIdentity(self, idy: Identity):
        assert isinstance(self, Wallet)
        if idy.role and idy.role not in (SPONSOR, STEWARD):
            raise AttributeError("invalid role: {}".format(idy.role))
        if idy.identifier in self._sponsored:
            raise RuntimeError("identifier already added")
        self._sponsored[idy.identifier] = idy
        req = idy.ledgerRequest()
        if req:
            if not req.identifier:
                req.identifier = self.defaultId
            self._pending.appendleft((req, idy.identifier))
        return len(self._pending)


class Wallet(PWallet, Sponsoring):
    clientNotPresentMsg = "The wallet does not have a client associated with it"

    def __init__(self, name: str):
        PWallet.__init__(self, name)
        Sponsoring.__init__(self)

        self._credMasterSecret = None
        self._attributes = {}       # type: Dict[(str, Identifier, Optional[Identifier]), Attribute]
        self._credDefs = {}         # type: Dict[(str, str, str), CredDef]
        self._credDefSks = {}       # type: Dict[(str, str, str), CredDefSk]
        self._credentials = {}      # type: Dict[str, Credential]
        # self._links = {}            # type: Dict[str, Link]
        self.lastKnownSeqs = {}     # type: Dict[str, int]
        # TODO Rename to `_links`
        self._linkInvitations = {}  # type: Dict[str, Link]
        self.knownIds = {}          # type: Dict[str, Identifier]
        self._claimDefs = {}        # type: Dict[ClaimDefKey, ClaimDef]
        # transactions not yet submitted
        self._pending = deque()     # type Tuple[Request, Tuple[str, Identifier, Optional[Identifier]]

        # pending transactions that have been prepared (probably submitted)
        self._prepared = {}         # type: Dict[(Identifier, int), Request]

        self.replyHandler = {
            ATTRIB: self._attribReply,
            GET_ATTR: self._getAttrReply,
            CRED_DEF: self._credDefReply,
            GET_CRED_DEF: self._getCredDefReply,
            NYM: self._nymReply,
            GET_NYM: self._getNymReply,
            GET_TXNS: self._getTxnsReply
        }

    @property
    def pendingCount(self):
        return len(self._pending)

    @staticmethod
    def _isMatchingName(source, target):
        return source == target or source.lower() in target.lower()

    def addClaimDef(self, cd: ClaimDef):
        self._claimDefs[
            (cd.key.name, cd.key.version, cd.key.claimDefSeqNo)] = cd

    def getClaimDefByKey(self, key: ClaimDefKey):
        return self._claimDefs.get(
            (key.name, key.version, key.claimDefSeqNo), None)

    def getMachingRcvdClaims(self, attributes):
        matchingLinkAndRcvdClaim = []
        matched = []

        for k, li in self._linkInvitations.items():
            for rc in li.receivedClaims.values():
                commonAttr = (set(attributes.keys()) - set(matched)).\
                    intersection(rc.values.keys())
                if commonAttr:
                    matchingLinkAndRcvdClaim.append((li, rc, commonAttr))
                    matched.extend(commonAttr)

        return matchingLinkAndRcvdClaim

    # TODO: Few of the below methods have duplicate code, need to refactor it
    def getMatchingLinksWithAvailableClaim(self, claimName):
        matchingLinkAndAvailableClaim = []
        for k, li in self._linkInvitations.items():
            for ac in li.availableClaims.values():
                if Wallet._isMatchingName(ac.claimDefKey.name, claimName):
                    matchingLinkAndAvailableClaim.append((li, ac))
        return matchingLinkAndAvailableClaim

    def getMatchingLinksWithReceivedClaim(self, claimName):
        matchingLinkAndReceivedClaim = []
        for k, li in self._linkInvitations.items():
            for rc in li.receivedClaims.values():
                if Wallet._isMatchingName(rc.defKey.name, claimName):
                    matchingLinkAndReceivedClaim.append((li, rc))
        return matchingLinkAndReceivedClaim

    def getMatchingLinksWithClaimReq(self, claimReqName):
        matchingLinkAndClaimReq = []
        for k, li in self._linkInvitations.items():
            for cr in li.claimRequests:
                if Wallet._isMatchingName(cr.name, claimReqName):
                    matchingLinkAndClaimReq.append((li, cr))
        return matchingLinkAndClaimReq

    def _buildClaimKey(self, providerIdr, claimName):
        return providerIdr + ":" + claimName

    def addAttribute(self, attrib: Attribute):
        """
        :param attrib: attribute to add
        :return: number of pending txns
        """
        self._attributes[attrib.key()] = attrib
        req = attrib.ledgerRequest()
        if req:
            self._pending.appendleft((req, attrib.key()))
        return len(self._pending)

    def hasAttribute(self, key: AttributeKey) -> bool:
        """
        Checks if attribute is present in the wallet
        @param name: Name of the attribute
        @return:
        """
        return bool(self.getAttribute(key))

    def getAttribute(self, key: AttributeKey):
        return self._attributes.get(key.key())

    def getAttributesForNym(self, idr: Identifier):
        return [a for a in self._attributes.values() if a.dest == idr]

    def addCredDef(self, credDef: CredDef):
        """
        :param credDef: credDef to add
        :return: number of pending txns
        """
        self._credDefs[credDef.key()] = credDef
        req = credDef.request
        if req:
            self._pending.appendleft((req, credDef.key()))
        return len(self._pending)

    def getCredDef(self, key: CredDefKey):
        return self._credDefs[key.key()]

    def addCredDefSk(self, credDefSk: CredDefSk):
        self._credDefSks[credDefSk.key()] = credDefSk

    def getCredDefSk(self, key: CredDefKey):
        return self._credDefSks.get(key.key())

    def addCredential(self, cred: Credential):
        self._credentials[cred.key()] = cred

    def getCredential(self, name: str):
        return self._credentials.get(name)

    def addMasterSecret(self, masterSecret):
        self._credMasterSecret = masterSecret

    def addLink(self, link: Link):
        self._links[link.key()] = link

    def getLink(self, name):
        return self._links.get(name)

    @property
    def masterSecret(self):
        return self._credMasterSecret

    @property
    def credNames(self):
        return self._credentials.keys()

    def addLastKnownSeqs(self, identifier, seqNo):
        self.lastKnownSeqs[identifier] = seqNo

    def getLastKnownSeqs(self, identifier):
        return self.lastKnownSeqs.get(identifier)

    def getPendingTxnRequests(self, *identifiers):
        if not identifiers:
            identifiers = self.ids.keys()
        else:
            identifiers = set(identifiers).intersection(set(self.ids.keys()))
        requests = []
        for identifier in identifiers:
            lastTxn = self.getLastKnownSeqs(identifier)
            op = {
                TARGET_NYM: identifier,
                TXN_TYPE: GET_TXNS,
            }
            if lastTxn:
                op[DATA] = lastTxn
            requests.append(self.signOp(op, identifier=identifier))
        return requests

    def preparePending(self):
        new = {}
        while self._pending:
            req, key = self._pending.pop()

            sreq = self.signRequest(req)
            new[req.identifier, req.reqId] = sreq, key
        self._prepared.update(new)
        # Return request in the order they were submitted
        return sorted([req for req, _ in new.values()],
                      key=operator.attrgetter("reqId"))

    def handleIncomingReply(self, observer_name, reqId, frm, result, numReplies):
        """
        Called by an external entity, like a Client, to notify of incoming
        replies
        :return:
        """
        preparedReq = self._prepared.get((result[IDENTIFIER], reqId))
        if not preparedReq:
            raise RuntimeError('no matching prepared value for {},{}'.
                               format(result[IDENTIFIER], reqId))
        typ = result.get(TXN_TYPE)
        if typ and typ in self.replyHandler:
            self.replyHandler[typ](result, preparedReq)
        else:
            raise NotImplementedError('No handler for {}'.format(typ))

    def _attribReply(self, result, preparedReq):
        _, attrKey = preparedReq
        attrib = self.getAttribute(AttributeKey(*attrKey))
        attrib.seqNo = result[F.seqNo.name]

    def _getAttrReply(self, result, preparedReq):
        # TODO: Confirm if we need to add the retrieved attribute to the wallet.
        # If yes then change the graph query on node to return the sequence
        # number of the attribute txn too.
        _, attrKey = preparedReq
        attrib = self.getAttribute(AttributeKey(*attrKey))
        # TODO: THE GET_ATTR reply should contain the sequence number of
        # the ATTRIB transaction
        # attrib.seqNo = result[F.seqNo.name]

    def _credDefReply(self, result, preparedReq):
        # TODO: Duplicate code from _attribReply, abstract this behavior,
        # Have a mixin like `HasSeqNo`
        _, key = preparedReq
        credDef = self.getCredDef(CredDefKey(*key))
        credDef.seqNo = result[F.seqNo.name]

    def _getCredDefReply(self, result, preparedReq):
        data = json.loads(result.get(DATA))
        keys = json.loads(data[KEYS])
        credDef = CredDef(data[NAME], data[VERSION],
                          result[TARGET_NYM], data[TYPE],
                          data[IP], data[PORT], keys)
        self.addCredDef(credDef)

    def _nymReply(self, result, preparedReq):
        target = result[TARGET_NYM]
        idy = self._sponsored.get(target)
        if idy:
            idy.seqNo = result[F.seqNo.name]
        else:
            raise NotImplementedError

    def _getNymReply(self, result, preparedReq):
        data = json.loads(result.get(DATA))
        nym = data.get(TARGET_NYM)
        idy = self.knownIds.get(nym)
        if idy:
            idy.role = data.get(ROLE)
            idy.sponsor = data.get(f.IDENTIFIER.nm)
            idy.last_synced = datetime.datetime.utcnow()
            # TODO: THE GET_NYM reply should contain the sequence number of
            # the NYM transaction

    def _getTxnsReply(self, result, preparedReq):
        # TODO
        print(result)
        # for now, just print and move on

    def pendRequest(self, req, key=None):
        self._pending.appendleft((req, key))

    def addLinkInvitation(self, linkInvitation):
        # self._linkInvitations[linkInvitation.name] = linkInvitation.\
        #     getDictToBeStored()
        self._linkInvitations[linkInvitation.name] = linkInvitation

    def getLinkInvitationByTarget(self, target: str):
        for k, li in self._linkInvitations.items():
            if li.remoteIdentifier == target:
                return li

    def getMatchingLinkInvitations(self, name: str):
        allMatched = []
        for k, v in self._linkInvitations.items():
            if name == k or name.lower() in k.lower():
                # liValues = v
                # li = LinkInvitation.getFromDict(k, v)
                allMatched.append(v)
        return allMatched

    # TODO: Is `requestAttribute` a better name?
    # def makeGetAttributeRequest(self, attrName: str, origin=None, dest=None):
    #     # # TODO: How do i move this to Attribute
    #     op = {
    #         TARGET_NYM: dest,
    #         TXN_TYPE: GET_ATTR,
    #         RAW: attrName
    #     }
    #     req = self.signOp(op)
    #     return self.prepReq(req)

    def requestAttribute(self, attrib: Attribute, sender):
        """
        :param attrib: attribute to add
        :return: number of pending txns
        """
        self._attributes[attrib.key()] = attrib
        req = attrib.getRequest(sender)
        if req:
            return self.prepReq(req, key=attrib.key())

    def requestIdentity(self, identity: Identity, sender):
        self.knownIds[identity.identifier] = identity
        req = identity.getRequest(sender)
        if req:
            return self.prepReq(req)

    def requestCredDef(self, credefKey: CredDefKey, sender):
        credDef = CredDef(*credefKey.key())
        self._credDefs[credefKey.key()] = credDef
        req = credDef.getRequest(sender)
        if req:
            return self.prepReq(req)

    def prepReq(self, req, key=None):
        self.pendRequest(req, key=key)
        return self.preparePending()[0]

    def getLinkByNonce(self, nonce) -> Optional[Link]:
        for _, li in self._linkInvitations.items():
            if li.nonce == nonce:
                return li
