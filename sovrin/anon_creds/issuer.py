from abc import abstractmethod
from typing import Sequence

from sovrin.anon_creds.cred_def import CredDef


class Issuer:

    @abstractmethod
    def __init__(self, id):
        pass

    @abstractmethod
    def addNewCredDef(self, attrNames, name, version,
                   p_prime=None, q_prime=None, ip=None, port=None) -> CredDef:
        pass

    @abstractmethod
    def getCredDef(self, name=None, version=None, attributes: Sequence[str] = None)-> CredDef:
        pass

    @abstractmethod
    def createCred(self, proverId, name, version, U):
        pass

