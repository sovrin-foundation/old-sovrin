import json
from _sha256 import sha256

from copy import deepcopy
from typing import Any, Dict, Union
from typing import Optional

from plenum.client.wallet import Wallet as PWallet
from plenum.common.txn import TXN_TYPE, RAW, ENC, HASH, TARGET_NYM, DATA
from plenum.common.types import Identifier
from plenum.common.types import Request
from sovrin.common.txn import ATTRIB, GET_TXNS
from sovrin.common.util import getSymmetricallyEncryptedVal

ENCODING = "utf-8"

Cryptonym = str


class AttributeKey:
    def __init__(self,
                 name: str,
                 dest: Optional[str]=None):
        self.name = name
        self.dest = dest

    def key(self):
        return self.name, self.dest


class Attribute(AttributeKey):
    def __init__(self,
                 name: str,
                 dest: str,
                 val: Any,
                 origin: str,
                 encKey: Optional[str]=None,
                 encType: Optional[str]=None,
                 hashed: bool=False):
        super().__init__(name, dest)
        assert isinstance(val, (str, dict))
        self.val = val
        self.origin = origin
        self.encKey = encKey
        self.encType = encType
        self.hashed = hashed


class CredDefKey:
    def __init__(self, name: str, version: str, dest: Optional[str]=None):
        self.name = name
        self.version = version
        self.dest = dest    # author of the credential definition

    def key(self):
        return self.name, self.version, self.dest


class CredDef(CredDefKey):
    def __init__(self, name: str, version: str, dest: str, typ: str, ip: str,
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
        self._attributes = {}  # type: Dict[(str, str), Attribute]
        self._credDefs = {}  # type: Dict[(str, str, str), CredDef]
        self._credDefSks = {}  # type: Dict[(str, str, str), CredDefSk]
        self._credentials = {}  # type: Dict[str, Credential]
        self._credMasterSecret = None
        self._links = {}  # type: Dict[str, Link]
        self.lastKnownSeqs = {}     # type: Dict[str, int]

    def signOp(self, op: Dict, identifier: Identifier=None) -> Request:
        """
        Signs the message if a signer is configured

        :param identifier: signing identifier; if not supplied the default for
            the wallet is used.
        :param op: Operation to be signed
        :return: a signed Request object
        """
        if op.get(TXN_TYPE) == ATTRIB:
            opCopy = deepcopy(op)
            keyName = {RAW, ENC, HASH}.intersection(set(opCopy.keys())).pop()
            opCopy[keyName] = sha256(opCopy[keyName].encode()).hexdigest()
            req = super().signRequest(Request(operation=opCopy),
                                      identifier=identifier)
            req.operation[keyName] = op[keyName]
            return req
        else:
            return self.signRequest(Request(operation=op),
                                    identifier=identifier)
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

    def addAttribute(self, attrib: Attribute):
        self._attributes[attrib.key()] = attrib

    def hasAttribute(self, key: AttributeKey) -> bool:
        """
        Checks if attribute is present in the wallet
        @param name: Name of the attribute
        @return:
        """
        return bool(self.getAttribute(key))

    def getAttribute(self, key: AttributeKey):
        return self._attributes.get(key.key())

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
