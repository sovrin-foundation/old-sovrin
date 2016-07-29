from typing import Any, Dict
from typing import Optional

from plenum.client.wallet import Wallet as PWallet

from sovrin.persistence.wallet_storage import WalletStorage

ENCODING = "utf-8"

Cryptonym = str


class Wallet(PWallet):
    clientNotPresentMsg = "The wallet does not have a client associated with it"

    def __init__(self, name: str, storage: WalletStorage):
        PWallet.__init__(self, name, storage=storage)

    def addAttribute(self,
                     name: str,
                     val: Any,
                     origin: str,
                     dest: Optional[str]=None,
                     encKey: Optional[str]=None,
                     encType: Optional[str] = None,
                     hashed: bool = False):
        self.storage.addAttribute(name, val, origin, dest, encKey, encType,
                                  hashed)

    def hasAttribute(self, name: str, dest: Optional[str]=None) -> bool:
        """
        Checks if attribute is present in the wallet
        @param name: Name of the attribute
        @return:
        """
        return bool(self.getAttribute(name, dest))

    def getAttribute(self, name: str, dest: Optional[str]=None):
        return self.storage.getAttribute(name, dest)

    @property
    def attributes(self):
        return self.storage.attributes

    def addCredDef(self, name: str, version: str, dest: str, typ: str, ip: str,
                   port: int, keys: Dict):
        self.storage.addCredDef(name, version, dest, typ, ip, port, keys)

    def getCredDef(self, name: str, version: str, dest: str = None):
        return self.storage.getCredDef(name, version, dest)

    def addCredDefSk(self, name: str, version: str, secretKey):
        self.storage.addCredDefSk(name, version, secretKey)

    def getCredDefSk(self, name: str, version: str):
        return self.storage.getCredDefSk(name, version)

    def addCredential(self, name: str, data: Dict):
        self.storage.addCredential(name, data)

    def getCredential(self, name: str):
        return self.storage.getCredential(name)

    def addMasterSecret(self, masterSecret):
        self.storage.addMasterSecret(masterSecret)

    @property
    def masterSecret(self):
        return self.storage.masterSecret

    @property
    def credNames(self):
        return self.storage.credNames

