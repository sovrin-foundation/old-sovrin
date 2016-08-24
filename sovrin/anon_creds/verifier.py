from abc import abstractmethod
from typing import Dict, Sequence

from sovrin.anon_creds.cred_def import CredDef

from anoncreds.protocol.types import PredicateProof, T


class Verifier:

    @abstractmethod
    def __init__(self, id):
        pass

    # TODO: mention return type
    @abstractmethod
    def generateNonce(self, interactionId):
        pass

    @abstractmethod
    def getCredDef(self, issuerId, name, version) -> CredDef:
        pass

    def verify(self, issuer, name, version, proof, nonce, attrs, revealedAttrs) -> bool:
        pass

    def fetchCredDef(self, issuer, name, version) -> CredDef:
        pass

    def verifyPredicateProof(self, **kwargs)-> bool:
        pass
