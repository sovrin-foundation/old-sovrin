import json
import operator

from collections import deque
from typing import Dict
from typing import Optional

from ledger.util import F
from plenum.client.wallet import Wallet as PWallet
from plenum.common.txn import TXN_TYPE, TARGET_NYM, DATA, \
    IDENTIFIER, NAME, VERSION, IP, PORT, KEYS, TYPE, NYM, STEWARD, ROLE
from plenum.common.types import Identifier
from sovrin.client.wallet.attribute import Attribute, AttributeKey
from sovrin.client.wallet.cred_def import CredDefKey, CredDef, CredDefSk
from sovrin.client.wallet.credential import Credential
from sovrin.client.wallet.link import Link
from sovrin.client.wallet.link_invitation import LinkInvitation
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

        self._attributes = {}  # type: Dict[(str, Identifier, Optional[Identifier]), Attribute]
        self._credDefs = {}  # type: Dict[(str, str, str), CredDef]
        self._credDefSks = {}  # type: Dict[(str, str, str), CredDefSk]
        self._credentials = {}  # type: Dict[str, Credential]
        self._credMasterSecret = None
        self._links = {}  # type: Dict[str, Link]
        self.lastKnownSeqs = {}     # type: Dict[str, int]
        self._linkInvitations = {}  # type: Dict[str, dict]  # TODO should DEPRECATE in favor of links

        # transactions not yet submitted
        self._pending = deque()  # type Tuple[Request, Tuple[str, Identifier, Optional[Identifier]]

        # pending transactions that have been prepared (probably submitted)
        self._prepared = {}  # type: Dict[(Identifier, int), Request]

        self.replyHandler = {
            ATTRIB: self._attribReply,
            GET_ATTR: self._getAttrReply,
            CRED_DEF: self._credDefReply,
            GET_CRED_DEF: self._getCredDefReply,
            NYM: self._nymReply,
            GET_NYM: self._getNymReply,
            GET_TXNS: self._getTxnsReply
        }

    # DEPR
    # def signOp(self, op: Dict, identifier: Identifier=None) -> Request:
    #     """
    #     Signs the message if a signer is configured
    #
    #     :param identifier: signing identifier; if not supplied the default for
    #         the wallet is used.
    #     :param op: Operation to be signed
    #     :return: a signed Request object
    #     """
    #     if op.get(TXN_TYPE) == ATTRIB:
    #         opCopy = deepcopy(op)
    #         keyName = {RAW, ENC, HASH}.intersection(set(opCopy.keys())).pop()
    #         opCopy[keyName] = sha256(opCopy[keyName].encode()).hexdigest()
    #         req = super().signRequest(Request(operation=opCopy),
    #                                   identifier=identifier)
    #         req.operation[keyName] = op[keyName]
    #         return req
    #     else:
    #         return super().signRequest(Request(operation=op),
    #                                    identifier=identifier)

        # DEPR
        # if msg[OPERATION].get(TXN_TYPE) == ATTRIB:
        #     msgCopy = deepcopy(msg)
        #     keyName = {RAW, ENC, HASH}.intersection(
        #         set(msgCopy[OPERATION].keys())).pop()
        #     msgCopy[OPERATION][keyName] = sha256(msgCopy[OPERATION][keyName]
        #                                            .encode()).hexdigest()
        #     msg[f.SIG.nm] = signer.sign(msgCopy)
        #     return msg
        # else:
        #     return super().sign(msg, signer)

    @property
    def pendingCount(self):
        return len(self._pending)

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

    # DEPR
    # def getAllAttributesForNym_DEPRECATED(self, nym, identifier=None):
    #     # TODO: Does this need to get attributes from the nodes?
    #     walletAttributes = self.wallet.attributes
    #     attributes = []
    #     for attr in walletAttributes:
    #         if TARGET_NYM in attr and attr[TARGET_NYM] == nym:
    #             if RAW in attr:
    #                 attributes.append({attr[NAME]: attr[RAW]})
    #             elif ENC in attr:
    #                 attributes.append(self._getDecryptedData(attr[ENC],
    #                                                          attr[SKEY]))
    #             elif HASH in attr:
    #                 attributes.append({attr[NAME]: attr[HASH]})
    #     return attributes

    # @property
    # def attributes(self):
    #     return self._attributes
    #

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

    # def addCredDef(self, credDef: CredDef):
    #     self._credDefs[credDef.key()] = credDef

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

    # def getNymRequest(self, nym: IDENTIFIER, requester: Identifier=None):
    #     op = {
    #         TARGET_NYM: nym,
    #         TXN_TYPE: GET_NYM,
    #     }
    #     return self.signOp(op, requester)

    def preparePending(self):
        new = {}
        while self._pending:
            req, key = self._pending.pop()

            sreq = self.signRequest(req)
            new[req.identifier, req.reqId] = sreq, key
        self._prepared.update(new)
        # Return request in the order they were submitted
        return sorted([req for req, _ in new.values()], key=operator.attrgetter("reqId"))

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
        pass

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
        raise NotImplementedError

    def _getTxnsReply(self, result, preparedReq):
        # TODO
        print(result)
        # for now, just print and move on

    def pendRequest(self, req):
        self._pending.appendleft((req, None))

    def addLinkInvitation(self, linkInvitation):
        self._linkInvitations[linkInvitation.name] = linkInvitation.\
            getDictToBeStored()

    def getMatchingLinkInvitations(self, name: str):
        allMatched = []
        for k, v in self._linkInvitations.items():
            if name == k or name.lower() in k.lower():
                liValues = v
                li = LinkInvitation.getFromDict(k, liValues)
                allMatched.append(li)
        return allMatched
