from typing import Optional, Dict

from plenum.common.txn import TXN_TYPE, DATA, NAME, VERSION, IP, PORT, KEYS, \
    TARGET_NYM, RAW
from plenum.common.types import Identifier
from sovrin.common.txn import CRED_DEF, GET_CRED_DEF
from sovrin.common.types import Request


class CredDefKey:
    def __init__(self, name: str, version: str, origin: Optional[Identifier]=None):
        self.name = name
        self.version = version
        self.origin = origin    # author of the credential definition

    def key(self):
        return self.name, self.version, self.origin


class CredDef(CredDefKey):
    def __init__(self, name: str, version: str, origin: Optional[Identifier]=None,
                 typ: str=None, ip: str=None,
                 port: int=None, keys: Dict=None,
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
            return Request(identifier=self.origin, operation=op)

    def _opForGet(self):
        op = {
            TARGET_NYM: self.origin,
            TXN_TYPE: GET_CRED_DEF,
            DATA: {
                NAME: self.name,
                VERSION: self.version,
            }
        }
        return op

    def getRequest(self, requestAuthor: Identifier):
        if not self.seqNo:
            return Request(identifier=requestAuthor, operation=self._opForGet())


class CredDefSk(CredDefKey):
    def __init__(self,
                 name: str,
                 version: str,
                 secretKey: str,
                 dest: Optional[str]=None):
        super().__init__(name, version, dest)
        self.secretKey = secretKey