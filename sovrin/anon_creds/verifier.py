from abc import abstractmethod
from typing import Any

from sovrin.anon_creds.cred_def import CredDef


class Verifier:

    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    # TODO: mention return type
    @abstractmethod
    def generateNonce(self, *args, **kwargs):
        pass

    @abstractmethod
    def getCredDef(self, *args, **kwargs) -> CredDef:
        pass

    @abstractmethod
    def fetchCredDef(self, *args, **kwargs) -> CredDef:
        pass

    @abstractmethod
    def verifyPredicateProof(self, *args, **kwargs)-> bool:
        pass

    @abstractmethod
    def verifyProof(cls, *args, **kwargs) -> bool:
        pass