import base64
import json
from typing import Dict

from ledger.stores.directory_store import DirectoryStore
from plenum.common.txn import NAME, TYPE, IP, PORT, KEYS, VERSION, TARGET_NYM
from sovrin.persistence.credential_def_store import CredDefStore


class CredDefStoreFile(CredDefStore):
    def __init__(self, baseDir: str, name: str):
        self.store = DirectoryStore(baseDir, name)

    @staticmethod
    def key(name: str, version: str, dest: str):
        key = "{}_{}_{}".format(name, version, dest)
        return base64.urlsafe_b64encode(key.encode()).decode()

    def addCredDef(self, name: str, version: str, dest: str, type: str, ip: str,
                     port: int, keys: Dict):
        key = self.key(name, version, dest)
        self.store.put(key, json.dumps({
            TYPE: type,
            IP: ip,
            PORT: port,
            KEYS: keys
        }))

    def getCredDef(self, name: str, version: str, dest: str = None):
        key = self.key(name, version, dest)
        value = self.store.get(key)
        if value:
            credDef = json.loads(value)
            credDef.update({
                NAME: name,
                VERSION: version,
                TARGET_NYM: dest
            })
            return credDef
