import json
from typing import Optional, Dict

from anoncreds.protocol.issuer_key import IssuerKey
from anoncreds.protocol.credential_definition import CredentialDefinition
from plenum.common.txn import TXN_TYPE, DATA, NAME, VERSION, TARGET_NYM, TYPE,\
    ORIGIN
from plenum.common.types import Identifier
from sovrin.common.txn import CRED_DEF, GET_CRED_DEF, ATTR_NAMES, ISSUER_KEY, \
    GET_ISSUER_KEY, REF
from sovrin.common.types import Request


class HasSeqNo:
    @property
    def seqNo(self):
        return self.uid

    @seqNo.setter
    def seqNo(self, value):
        self.uid = value


class ClaimDef(CredentialDefinition, HasSeqNo):
    def __init__(self,
                 name: str,
                 version: str,
                 origin: Optional[Identifier] = None,
                 seqNo: Optional[int] = None,
                 attrNames=None,
                 secretKey: Optional[str]=None,     # uid of the Cred Def secret key
                 typ: str=None,
                 ):
        super().__init__(uid=seqNo,
                         attrNames=attrNames,
                         name=name,
                         version=version)
        self.typ = typ
        self.origin = origin
        self.secretKey = secretKey

    @property
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
                }
            }
            return Request(identifier=self.origin, operation=op)

    def _opForGet(self):
        op = {
            TARGET_NYM: self.origin,    # TODO: Should be origin
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

    @property
    def attributes(self):
        return \
            'Attributes:' + '\n      ' + \
            format("\n      ".join(
            ['{}'.format(k)
             for k in self.attrNames]))

    def __str__(self):
        return \
            'Name: ' + self.name + '\n' + \
            'Version: ' + self.version + '\n' + \
            self.attributes


class IssuerPubKey(IssuerKey, HasSeqNo):
    def __init__(self, claimDefSeqNo: int,
                 origin, N=None, R=None, S=None, Z=None, secretKeyUid=None,
                 seqNo: Optional[int]=None):
        if all([x is not None for x in (N, R, S, Z)]):
            self.initPubKey(seqNo, N, R, S, Z)
        else:
            self.uid = seqNo
        self.claimDefSeqNo = claimDefSeqNo
        # TODO: Remove this
        self.secretKeyUid = secretKeyUid
        self.origin = origin

    # TODO: Remove this late initialisation.
    def initPubKey(self, seqNo, N, R, S, Z):
        IssuerKey.__init__(self, seqNo, N, R, S, Z)

    @property
    def key(self):
        return self.origin, self.claimDefSeqNo

    @property
    def request(self):
        if not self.seqNo:
            assert self.origin is not None
            R_str = {k: str(v) for k, v in self.R.items()}
            op = {
                TXN_TYPE: ISSUER_KEY,
                REF: self.claimDefSeqNo,
                DATA: {
                    "N": str(self.N),
                    "R": R_str,
                    "S": str(self.S),
                    "Z": str(self.Z)
                }
            }
            return Request(identifier=self.origin, operation=op)

    def _opForGet(self):
        op = {
            TXN_TYPE: GET_ISSUER_KEY,
            REF: self.claimDefSeqNo,
            ORIGIN: self.origin
        }
        return op

    def getRequest(self, requestAuthor: Identifier):
        if not self.seqNo:
            return Request(identifier=requestAuthor, operation=self._opForGet())
