from typing import Any, Dict
from typing import Optional

from plenum.client.wallet import Wallet as PWallet

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
        self.val = val
        self.origin = origin
        self.encKey = encKey
        self.encType = encType
        self.hashed = hashed


class CredDefKey:
    def __init__(self, name: str, version: str, dest: Optional[str]=None):
        self.name = name
        self.version = version
        self.dest = dest

    def key(self):
        return self.name, self.version, self.dest


class CredDef(CredDefKey):
    def __init__(self, name: str, version: str, dest: str, typ: str, ip: str,
                 port: int, keys: Dict):
        super().__init__(name, version, dest)  # TODO: JAL Why is dest included?
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
