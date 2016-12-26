import base64
import json
from typing import Any, Optional

from ledger.stores.directory_store import DirectoryStore
from plenum.common.txn import ORIGIN, TARGET_NYM, NAME, RAW, ENC, HASH

from sovrin.common.txn import SKEY, ENC_TYPE
from sovrin.persistence.attribute_store import AttributeStore


class AttributeStoreFile(AttributeStore):
    def __init__(self, baseDir: str, name: str):
        self.store = DirectoryStore(baseDir, name)

    @staticmethod
    def attrKey(name: str, dest: Optional[str] = None):
        dest = dest or ""
        key = "{}_{}".format(name, dest)
        return base64.urlsafe_b64encode(key.encode()).decode()

    @staticmethod
    def attrKeyParts(attrKey: str):
        key = base64.urlsafe_b64decode(attrKey).decode()
        return str.rsplit(key, "_", 1)

    @staticmethod
    def constructAttrData(fileData: str, name: str, dest: Optional[str]=None):
        attr = json.loads(fileData)
        attr[NAME] = name
        if dest:
            attr[TARGET_NYM] = dest
        return attr

    # TODO: May be need to provide hash type also, assuming sha256 for now
    def addAttribute(self, name: str, val: Any, origin: str,
                     dest: Optional[str]=None, encKey: Optional[str]=None,
                     encType: Optional[str]=None, hashed: bool=False):
        key = self.attrKey(name, dest)

        if hashed:
            dataKeyName = HASH
        elif encKey:
            dataKeyName = ENC
        else:
            dataKeyName = RAW
        value = {dataKeyName: val, ORIGIN: origin}
        if encKey:
            value.update({SKEY: encKey})
        if encType:
            value.update({ENC_TYPE: encType})
        self.store.put(key, value=json.dumps(value))

    def getAttribute(self, name: str, dest: Optional[str] = None):
        key = self.attrKey(name, dest)
        value = self.store.get(key)
        if value:
            return self.constructAttrData(value, name, dest)

    @property
    def attributes(self):
        return [self.constructAttrData(val, *self.attrKeyParts(key))
                for key, val in self.store.iterator()]
