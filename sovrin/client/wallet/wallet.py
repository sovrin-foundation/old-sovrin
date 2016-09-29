import json

import datetime
import uuid

import operator

from collections import deque
from typing import Dict
from typing import Optional

from ledger.util import F
from plenum.client.wallet import Wallet as PWallet
from plenum.common.error import fault
from plenum.common.txn import TXN_TYPE, TARGET_NYM, DATA, \
    IDENTIFIER, NAME, VERSION, IP, PORT, KEYS, TYPE, NYM, STEWARD, ROLE, RAW, \
    ORIGIN
from plenum.common.types import Identifier, f
from sovrin.client.wallet.attribute import Attribute, AttributeKey
from sovrin.client.wallet.claim import ClaimDefKey, ClaimDef
from sovrin.client.wallet.cred_def import CredDef, IssuerPubKey
from sovrin.client.wallet.credential import Credential
from sovrin.client.wallet.link import Link
from sovrin.common.txn import ATTRIB, GET_TXNS, GET_ATTR, CRED_DEF, GET_CRED_DEF, \
    GET_NYM, SPONSOR, ATTR_NAMES, ISSUER_KEY, GET_ISSUER_KEY, REFERENCE
from sovrin.common.identity import Identity
from sovrin.common.types import Request

from anoncreds.protocol.utils import strToCharmInteger

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
            self.pendRequest(req, idy.identifier)
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
        self._issuerSks = {}
        self._issuerPks = {}
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
            GET_TXNS: self._getTxnsReply,
            ISSUER_KEY: self._issuerKeyReply,
            GET_ISSUER_KEY: self._getIssuerKeyReply,
        }

    @property
    def pendingCount(self):
        return len(self._pending)

    @staticmethod
    def _isMatchingName(source, target):
        return source == target or source.lower() in target.lower()

    def addClaimDef(self, cd: ClaimDef):
        self._claimDefs[cd.key.key] = cd

    def getClaimDefByKey(self, key: ClaimDefKey):
        return self._claimDefs.get(key.key)

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
            self.pendRequest(req, attrib.key())
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
            self.pendRequest(req, credDef.key())
        return len(self._pending)

    def getCredDef(self, key=None, seqNo=None):
        assert key or seqNo
        if key:
            return self._credDefs.get(key)
        else:
            for _, cd in self._credDefs.items():
                if cd.seqNo == seqNo:
                    return cd

    def addCredDefSk(self, credDefSk):
        uid = str(uuid.uuid4())
        self._credDefSks[uid] = credDefSk
        return uid

    def getCredDefSk(self, uid):
        return self._credDefSks.get(uid)

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

    def pendSyncRequests(self):
        pendingTxnsReqs = self.getPendingTxnRequests()
        for req in pendingTxnsReqs:
            self.pendRequest(req)

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
        credDef = self.getCredDef(key)
        credDef.seqNo = result[F.seqNo.name]

    def _getCredDefReply(self, result, preparedReq):
        data = json.loads(result.get(DATA))
        credDef = self.getCredDef((data.get(NAME), data.get(VERSION),
                                   data.get(ORIGIN)))
        if credDef:
            if not credDef.seqNo:
                credDef.seqNo = data.get(F.seqNo.name)
        else:
            credDef = CredDef(seqNo=data.get(F.seqNo.name),
                              attrNames=data.get(ATTR_NAMES).split(","),
                              name=data[NAME],
                              version=data[VERSION],
                              origin=data[ORIGIN],  # TODO should
                              typ=data[TYPE])
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

    def _issuerKeyReply(self, result, preparedReq):
        data = result.get(DATA)
        ref = result.get(REFERENCE)
        key = self._getMatchingIssuerKey(data)
        if key and self._issuerPks[key].claimDefSeqNo == ref:
            self._issuerPks[key].seqNo = result.get(F.seqNo.name)
            return self._issuerPks[key].seqNo
        else:
            raise Exception("Not found appropriate issuer key to update")

    def _getIssuerKeyReply(self, result, preparedReq):
        data = json.loads(result.get(DATA))
        key = data.get(ORIGIN), data.get(REFERENCE)
        isPk = self.getIssuerPublicKey(key)
        keys = data.get(DATA)
        for k in ('N', 'S', 'Z'):
            keys[k] = strToCharmInteger(keys[k])
        for k in keys['R']:
            keys['R'][k] = strToCharmInteger(keys['R'][k])
        isPk.initPubKey(data.get(F.seqNo.name), keys['N'], keys['R'],
                        keys['S'], keys['Z'])

    def _getMatchingIssuerKey(self, data):
        for key, pk in self._issuerPks.items():
            if str(pk.N) == data.get("N") and str(pk.S) == data.get("S") and str(pk.Z) == data.get("Z"):
                matches = 0
                for k, v in pk.R.items():
                    if str(pk.R.get(k)) == data.get("R").get(k):
                        matches += 1
                    else:
                        break
                if matches == len(pk.R):
                    return key
        return None

    def pendRequest(self, req, key=None):
        self._pending.appendleft((req, key))

    def addLinkInvitation(self, linkInvitation):
        self._linkInvitations[linkInvitation.name] = linkInvitation

    def getLinkInvitationByTarget(self, target: str) -> Link:
        for k, li in self._linkInvitations.items():
            if li.remoteIdentifier == target:
                return li

    def getLinkInvitation(self, name: str):
        return self._linkInvitations.get(name)

    def getMatchingLinkInvitations(self, name: str):
        allMatched = []
        for k, v in self._linkInvitations.items():
            if name == k or name.lower() in k.lower():
                allMatched.append(v)
        return allMatched

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

    def requestCredDef(self, credDefKey, sender):
        name, version, origin = credDefKey
        credDef = CredDef(name=name, version=version, origin=origin)
        self._credDefs[credDefKey] = credDef
        req = credDef.getRequest(sender)
        if req:
            return self.prepReq(req)

    def requestIssuerKey(self, issuerKey, sender):
        origin, claimDefSeqNo = issuerKey
        isPk = IssuerPubKey(origin=origin, claimDefSeqNo=claimDefSeqNo)
        self._issuerPks[issuerKey] = isPk
        req = isPk.getRequest(sender)
        if req:
            return self.prepReq(req)

    def prepReq(self, req, key=None):
        self.pendRequest(req, key=key)
        return self.preparePending()[0]

    def getLinkByNonce(self, nonce) -> Optional[Link]:
        for _, li in self._linkInvitations.items():
            if li.nonce == nonce:
                return li

    def addIssuerSecretKey(self, issuerSk):
        self._issuerSks[issuerSk.uid] = issuerSk
        return issuerSk.uid

    def getIssuerSecretKey(self, uid):
        return self._issuerSks.get(uid)

    def addIssuerPublicKey(self, issuerPk):
        self._issuerPks[issuerPk.key] = issuerPk
        req = issuerPk.request
        if req:
            self.pendRequest(req, None)
        return len(self._pending)

    def getIssuerPublicKey(self, key):
        return self._issuerPks.get(key)

    def getIssuerPublicKeyForClaimDef(self, claimDefSeqNo):
        # Assuming only one identifier per claimDefSeqNo
        for k, v in self._issuerPks.items():
            if k[1] == claimDefSeqNo:
                return v

    def getAvailableClaimList(self):
        resp = []
        for k, v in self._credDefs.items():
            ipk = self.getIssuerPublicKeyForClaimDef(v.seqNo)
            resp.append((v, ipk))
        return resp

