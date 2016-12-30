import datetime
import json
import operator
from collections import deque
from typing import Dict
from typing import Optional

from ledger.util import F
from plenum.client.wallet import Wallet as PWallet
from plenum.common.did_method import DidMethods
from plenum.common.log import getlogger
from plenum.common.txn import TXN_TYPE, TARGET_NYM, DATA, \
    IDENTIFIER, NYM, ROLE, VERKEY
from plenum.common.types import Identifier, f

from sovrin.client.wallet.attribute import Attribute, AttributeKey
from sovrin.client.wallet.link import Link
from sovrin.client.wallet.sponsoring import Sponsoring
from sovrin.common.did_method import DefaultDidMethods
from sovrin.common.exceptions import LinkNotFound
from sovrin.common.identity import Identity
from sovrin.common.txn import ATTRIB, GET_TXNS, GET_ATTR, GET_NYM

ENCODING = "utf-8"

logger = getlogger()


# TODO: Maybe we should have a thinner wallet which should not have ProverWallet
class Wallet(PWallet, Sponsoring):
    clientNotPresentMsg = "The wallet does not have a client associated with it"

    def __init__(self,
                 name: str,
                 supportedDidMethods: DidMethods=None):
        PWallet.__init__(self,
                         name,
                         supportedDidMethods or DefaultDidMethods)
        Sponsoring.__init__(self)
        self._attributes = {}  # type: Dict[(str, Identifier,
        # Optional[Identifier]), Attribute]

        self._links = {}  # type: Dict[str, Link]
        self.knownIds = {}  # type: Dict[str, Identifier]

        # transactions not yet submitted
        self._pending = deque()  # type Tuple[Request, Tuple[str, Identifier,
        #  Optional[Identifier]]

        # pending transactions that have been prepared (probably submitted)
        self._prepared = {}  # type: Dict[(Identifier, int), Request]
        self.lastKnownSeqs = {}  # type: Dict[str, int]

        self.replyHandler = {
            ATTRIB: self._attribReply,
            GET_ATTR: self._getAttrReply,
            NYM: self._nymReply,
            GET_NYM: self._getNymReply,
            GET_TXNS: self._getTxnsReply,
        }

    @property
    def pendingCount(self):
        return len(self._pending)

    @staticmethod
    def _isMatchingName(needle, haystack):
        return needle.lower() in haystack.lower()

    # TODO: The names getMatchingLinksWithAvailableClaim and
    # getMatchingLinksWithReceivedClaim should be fixed. Difference between
    # `AvailableClaim` and `ReceivedClaim` is that for ReceivedClaim we
    # have attribute values from issuer.

    # TODO: Few of the below methods have duplicate code, need to refactor it
    def getMatchingLinksWithAvailableClaim(self, claimName=None):
        matchingLinkAndAvailableClaim = []
        for k, li in self._links.items():
            for cl in li.availableClaims:
                if not claimName or Wallet._isMatchingName(claimName, cl[0]):
                    matchingLinkAndAvailableClaim.append((li, cl))
        return matchingLinkAndAvailableClaim

    def getMatchingLinksWithClaimReq(self, claimReqName, linkName=None):
        matchingLinkAndClaimReq = []
        for k, li in self._links.items():
            for cpr in li.claimProofRequests:
                if Wallet._isMatchingName(claimReqName, cpr.name):
                    if linkName is None or Wallet._isMatchingName(linkName,
                                                                  li.name):
                        matchingLinkAndClaimReq.append((li, cpr))
        return matchingLinkAndClaimReq

    def addAttribute(self, attrib: Attribute):
        """
        Used to create a new attribute on Sovrin
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

    def addLink(self, link: Link):
        self._links[link.key] = link

    def getLink(self, name, required=False) -> Link:
        l = self._links.get(name)
        if not l and required:
            logger.debug("Wallet has links {}".format(self._links))
            raise LinkNotFound(l.name)
        return l

    def addLastKnownSeqs(self, identifier, seqNo):
        self.lastKnownSeqs[identifier] = seqNo

    def getLastKnownSeqs(self, identifier):
        return self.lastKnownSeqs.get(identifier)

    def getPendingTxnRequests(self, *identifiers):
        if not identifiers:
            identifiers = self.idsToSigners.keys()
        else:
            identifiers = set(identifiers).intersection(
                set(self.idsToSigners.keys()))
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

    def handleIncomingReply(self, observer_name, reqId, frm, result,
                            numReplies):
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
            # else:
            #    raise NotImplementedError('No handler for {}'.format(typ))

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
        if DATA in result:
            attrib.value = result[DATA]
            attrib.seqNo = result[F.seqNo.name]
        else:
            logger.debug("No attribute found")

    def _nymReply(self, result, preparedReq):
        target = result[TARGET_NYM]
        idy = self._sponsored.get(target)
        if idy:
            idy.seqNo = result[F.seqNo.name]
        else:
            logger.error("Target {} not found in sponsored".format(target))
            raise KeyError

    def _getNymReply(self, result, preparedReq):
        jsonData = result.get(DATA)
        if jsonData:
            data = json.loads(jsonData)
            nym = data.get(TARGET_NYM)
            idy = self.knownIds.get(nym)
            if idy:
                idy.role = data.get(ROLE)
                idy.sponsor = data.get(f.IDENTIFIER.nm)
                idy.last_synced = datetime.datetime.utcnow()
                idy.verkey = data.get(VERKEY)
                # TODO: THE GET_NYM reply should contain the sequence number of
                # the NYM transaction
        else:
            raise ValueError("'DATA' in reply was None")

    def _getTxnsReply(self, result, preparedReq):
        # TODO
        pass

    def pendRequest(self, req, key=None):
        self._pending.appendleft((req, key))

    def getLinkInvitationByTarget(self, target: str) -> Link:
        for k, li in self._links.items():
            if li.remoteIdentifier == target:
                return li

    def getLinkInvitation(self, name: str):
        return self._links.get(name)

    def getMatchingLinks(self, name: str):
        allMatched = []
        for k, v in self._links.items():
            if self._isMatchingName(name, k):
                allMatched.append(v)
        return allMatched

    # TODO: sender by default should be `self.defaultId`
    def requestAttribute(self, attrib: Attribute, sender):
        """
        Used to get a raw attribute from Sovrin
        :param attrib: attribute to add
        :return: number of pending txns
        """
        self._attributes[attrib.key()] = attrib
        req = attrib.getRequest(sender)
        if req:
            return self.prepReq(req, key=attrib.key())

    # TODO: sender by default should be `self.defaultId`
    def requestIdentity(self, identity: Identity, sender):
        # Used to get a nym from Sovrin
        self.knownIds[identity.identifier] = identity
        req = identity.getRequest(sender)
        if req:
            return self.prepReq(req)

    def prepReq(self, req, key=None):
        self.pendRequest(req, key=key)
        return self.preparePending()[0]

    # DEPR
    # Why shouldn't we fetch link by nonce
    def getLinkByNonce(self, nonce) -> Optional[Link]:
        for _, li in self._links.items():
            if li.invitationNonce == nonce:
                return li

    def getLinkByInternalId(self, internalId) -> Optional[Link]:
        for _, li in self._links.items():
            if li.internalId == internalId:
                return li

    def getIdentity(self, idr):
        # TODO, Question: Should it consider self owned identities too or
        # should it just have identities that are retrieved from the DL
        return self.knownIds.get(idr)