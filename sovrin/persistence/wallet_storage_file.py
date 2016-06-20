import json
from typing import Any, Dict

from ledger.stores.text_file_store import TextFileStore
from plenum.persistence.wallet_storage_file import WalletStorageFile \
    as PWalletStorageFile
from sovrin.persistence.attribute_store_file import AttributeStoreFile
from sovrin.persistence.credential_def_store_file import CredDefStoreFile
from sovrin.persistence.wallet_storage import WalletStorage


class WalletStorageFile(WalletStorage, PWalletStorageFile):
    def __init__(self, walletDir: str):
        PWalletStorageFile.__init__(self, walletDir)
        attrsDirName = "attributes"
        credDefDirName = "credential_definitions"
        credFileName = "credentials"
        dataDir = self.getDataLocation()
        self.attrStore = AttributeStoreFile(dataDir, attrsDirName)
        # type: AttributeStoreFile
        self.credDefStore = CredDefStoreFile(dataDir, credDefDirName)
        # type: CredDefStoreFile
        self.credStore = TextFileStore(dataDir, credFileName,
                                       storeContentHash=False)

    def addAttribute(self, name: str, val: Any, origin: str, dest: str = None,
                     encKey: str = None, encType: str = None,
                     hashed: bool = False):
        self.attrStore.addAttribute(name, val, origin, dest, encKey, encType,
                                    hashed)

    def getAttribute(self, name: str, dest: str = None):
        return self.attrStore.getAttribute(name, dest)

    @property
    def attributes(self):
        return self.attrStore.attributes

    def addCredDef(self, name: str, version: str, dest: str, type: str, ip: str,
                   port: int, keys: Dict):
        self.credDefStore.addCredDef(name, version, dest, type, ip, port, keys)

    def getCredDef(self, name: str, version: str, dest: str = None):
        self.credDefStore.getCredDef(name, version)

    def addCredential(self, name: str, data: Dict):
        self.credStore.put(key=name, value=json.dumps(data))

    def getCredential(self, name: str):
        self.credStore.get(name)
