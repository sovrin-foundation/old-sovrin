from typing import Optional, Dict

from anoncreds.protocol.credential_definition import CredentialDefinition
from plenum.common.txn import TXN_TYPE, DATA, NAME, VERSION, IP, PORT, KEYS, \
    TARGET_NYM, RAW, TYPE, ATTR_NAMES
from plenum.common.types import Identifier
from sovrin.common.txn import CRED_DEF, GET_CRED_DEF
from sovrin.common.types import Request


# DEPR
# class CredDefKey:
#     def __init__(self,
#                  name: str,
#                  version: str,
#                  origin: Optional[Identifier]=None):
#         self.name = name
#         self.version = version
#         self.origin = origin    # author of the credential definition


class CredDef(CredentialDefinition):
    def __init__(self,
                 seqNo: Optional[int],
                 attrNames,
                 name: str,
                 version: str,
                 secretKey: Optional[str]=None,    # uid of the Cred Def secret key
                 origin: Optional[Identifier]=None,
                 typ: str=None,
                 # DEPR
                 # ip: str=None,
                 # port: int=None,
                 # keys: Dict=None
                 ):
        super().__init__(uid=seqNo,
                         attrNames=attrNames,
                         name=name,
                         version=version)
        self.typ = typ
        self.origin = origin
        # DEPR
        # self.ip = ip
        # self.port = port
        # self.keys = keys
        # self.seqNo = seqNo

    @property
    def seqNo(self):
        return self.uid

    @seqNo.setter
    def seqNo(self, value):
        self.uid = value

    def key(self):
        return self.name, self.version, self.origin

    @property
    def request(self):
        if not self.seqNo:
            assert self.origin is not None
            op = {
                TXN_TYPE: CRED_DEF,
                DATA: {
                    NAME: self.name,
                    VERSION: self.version,
                    TYPE: self.typ,
                    ATTR_NAMES: ",".join(self.attrNames)
                    # DEPR
                    # IP: self.ip,
                    # PORT: self.port,
                    # KEYS: self.keys,
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


# class CredDefSk(CredDefKey):
#     def __init__(self,
#                  name: str,
#                  version: str,
#                  secretKey: str,
#                  dest: Optional[str]=None):
#         super().__init__(name, version, dest)
#         self.secretKey = secretKey
