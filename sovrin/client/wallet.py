import json
from _sha256 import sha256
from collections import deque

from copy import deepcopy
from enum import unique, IntEnum
from typing import Any, Dict, Union, TypeVar
from typing import Optional

from collections import OrderedDict
from typing import Tuple

from ledger.util import F
from plenum.client.wallet import Wallet as PWallet
from plenum.common.txn import TXN_TYPE, RAW, ENC, HASH, TARGET_NYM, DATA, \
    IDENTIFIER
from plenum.common.types import Identifier, f
from sovrin.common.types import Request
from sovrin.common.txn import ATTRIB, GET_TXNS


ENCODING = "utf-8"

Cryptonym = str


@unique
class LedgerStore(IntEnum):
    """
    How to store an attribute on the distributed ledger.

    1. DONT: don't store on public ledger
    2. HASH: store just a hash
    3. ENC: store encrypted
    4. RAW: store in plain text
    """
    DONT = 1
    HASH = 2
    ENC = 3
    RAW = 4

    @property
    def isWriting(self) -> bool:
        """
        Return whether this transaction needs to be written
        """
        return self != self.DONT


class AttributeKey:
    def __init__(self,
                 name: str,
                 origin: Identifier,
                 dest: Optional[Identifier]=None):
        self.name = name
        self.origin = origin
        self.dest = dest

    def key(self):
        return self.name, self.origin, self.dest

Value = TypeVar('Value', str, dict)


class Attribute(AttributeKey):
    # TODO we want to store a history of the attribute changes
    def __init__(self,
                 name: str,  # local human friendly name
                 value: Value,
                 origin: Identifier,  # authoring attribute
                 dest: Optional[Identifier]=None,  # target
                 ledgerStore: LedgerStore=LedgerStore.DONT,
                 encKey: Optional[str]=None,  # encryption key
                 seqNo: Optional[int]=None):  # ledger sequence number
        super().__init__(name, origin, dest)
        self.value = value
        self.ledgerStore = ledgerStore
        self.encKey = encKey
        self.seqNo = seqNo

    def _op(self):
        op = {
            TXN_TYPE: ATTRIB
        }
        if self.dest:
            op[TARGET_NYM] = self.dest
        if self.ledgerStore == LedgerStore.RAW:
            op[RAW] = self.value
        elif self.ledgerStore == LedgerStore.ENC:
            raise NotImplementedError
        elif self.ledgerStore == LedgerStore.HASH:
            raise NotImplementedError
        elif self.ledgerStore == LedgerStore.DONT:
            raise RuntimeError("This attribute cannot be stored externally")
        else:
            raise RuntimeError("Unknown ledgerStore: {}".format(self.ledgerStore))
        return op

    def ledgerRequest(self):
        """
        Generates a Request object to be submitted to the ledger.
        :return: a Request to be submitted, or None if it shouldn't be written
        """
        if self.ledgerStore.isWriting and not self.seqNo:
            assert self.origin is not None
            return Request(identifier=self.origin,
                           operation=self._op())


class CredDefKey:
    def __init__(self, name: str, version: str, dest: Optional[Identifier]=None):
        self.name = name
        self.version = version
        self.dest = dest    # author of the credential definition

    def key(self):
        return self.name, self.version, self.dest


class CredDef(CredDefKey):
    def __init__(self, name: str, version: str, dest: Optional[Identifier],
                 typ: str, ip: str,
                 port: int, keys: Dict):
        super().__init__(name, version, dest)
        self.typ = typ
        self.ip = ip
        self.port = port
        self.keys = keys


class CredDefSk(CredDefKey):
    def __init__(self,
                 name: str,
                 version: str,
                 secretKey: str,
                 dest: Optional[str]=None):
        super().__init__(name, version, dest)
        self.secretKey = secretKey


class Credential:
    def __init__(self, name: str, data: Dict):
        self.name = name
        self.data = data

    def key(self):
        return self.name


class Link:
    def __init__(self, name):
        self.name = name

    def key(self):
        return self.name


class Wallet(PWallet):
    clientNotPresentMsg = "The wallet does not have a client associated with it"

    def __init__(self, name: str):
        PWallet.__init__(self, name)
        self._attributes = {}  # type: Dict[(str, Identifier, Optional[Identifier]), Attribute]
        self._credDefs = {}  # type: Dict[(str, str, str), CredDef]
        self._credDefSks = {}  # type: Dict[(str, str, str), CredDefSk]
        self._credentials = {}  # type: Dict[str, Credential]
        self._credMasterSecret = None
        self._links = {}  # type: Dict[str, Link]
        self.lastKnownSeqs = {}     # type: Dict[str, int]

        # transactions not yet submitted
        self._pending = deque()  # type Tuple[Request, Tuple[str, Identifier, Optional[Identifier]]

        # pending transactions that have been prepared (probably submitted)
        self._prepared = {}  # type: Dict[(Identifier, int), Request]

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
        return [a for a in self._attributes if a.dest == idr]

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
        self._credDefs[credDef.key()] = credDef

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
            req, attrKey = self._pending.pop()

            sreq = self.signRequest(req)
            new[req.identifier, req.reqId] = sreq, attrKey
        self._prepared.update(new)
        return [req for req, _ in new.values()]

    def handleIncomingReply(self, observer_name, reqId, frm, result, numReplies):
        """
        Called by an external entity, like a Client, to notify of incoming
        replies
        :return:
        """
        find = self._prepared.get((result[IDENTIFIER], reqId))
        if not find:
            raise RuntimeError('no matching prepared value for {},{}'.
                               format(result[IDENTIFIER], reqId))
        if result[TXN_TYPE] == ATTRIB:
            sreq, attrKey = find
            attrib = self.getAttribute(AttributeKey(*attrKey))
            attrib.seqNo = result[F.seqNo.name]
        else:
            raise NotImplementedError
