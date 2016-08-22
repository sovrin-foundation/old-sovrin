from abc import abstractmethod
from typing import Sequence


class Issuer:

    @abstractmethod
    def __init__(self, id):
        pass

    @abstractmethod
    def newCredDef(self, attrNames, name, version,
                   p_prime=None, q_prime=None, ip=None, port=None):
        pass

    @abstractmethod
    def getCredDef(self, name=None, version=None, attributes: Sequence[str] = None):
        pass

    @abstractmethod
    def createCred(self, proverId, name, version, U):
        pass

