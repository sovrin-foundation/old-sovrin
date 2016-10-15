from typing import Dict

from anoncreds.protocol.utils import strToCharmInteger
from anoncreds.protocol.types import Credential as CredType


# A credential object is issued by an issuer to a prover for a particular
# issuer key. The prover is identified by a unique prover id. The wallet knows
# which prover is the owner of this credential
class Credential:
    def __init__(self, issuerKeyId: int, A, e, v):
        self.issuerKeyId = issuerKeyId
        self.A = strToCharmInteger(A) if isinstance(A, str) else A
        self.e = strToCharmInteger(e) if isinstance(e, str) else e
        self.v = strToCharmInteger(v) if isinstance(v, str) else v

    @property
    def key(self):
        return self.issuerKeyId

    @classmethod
    def buildFromIssuerProvidedCred(cls, issuerKeyId, A, e, v, vprime):
        vprime = strToCharmInteger(vprime) if isinstance(vprime, str) else vprime
        cred = cls(issuerKeyId, A, e, v)
        cred.v += vprime
        return cred

    @property
    def toNamedTuple(self):
        return CredType(self.A, self.e, self.v)
