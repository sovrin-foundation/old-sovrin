from typing import Optional, Dict

from plenum.common.txn import TXN_TYPE, DATA, NAME, VERSION, IP, PORT, KEYS
from plenum.common.types import Identifier
from sovrin.common.txn import CRED_DEF
from sovrin.common.types import Request


class CredDefKey:
    def __init__(self, name: str, version: str, origin: Optional[Identifier]=None):
        self.name = name
        self.version = version
        self.origin = origin    # author of the credential definition

    def key(self):
        return self.name, self.version, self.origin


class CredDef(CredDefKey):
    def __init__(self, name: str, version: str, origin: Optional[Identifier],
                 typ: str, ip: str,
                 port: int, keys: Dict,
                 seqNo: Optional[int] = None):
        super().__init__(name, version, origin)
        self.typ = typ
        self.ip = ip
        self.port = port
        self.keys = keys
        self.seqNo = seqNo

    @property
    def request(self):
        if not self.seqNo:
            assert self.origin is not None
            op = {
                TXN_TYPE: CRED_DEF,
                DATA: {
                    NAME: self.name,
                    VERSION: self.version,
                    IP: self.ip,
                    PORT: self.port,
                    KEYS: self.keys,
                }
            }
            return Request(identifier=self.origin,
                           operation=op)


class CredDefSk(CredDefKey):
    def __init__(self,
                 name: str,
                 version: str,
                 secretKey: str,
                 dest: Optional[str]=None):
        super().__init__(name, version, dest)
        self.secretKey = secretKey