from abc import abstractmethod
from typing import Sequence

from sovrin.anon_creds.cred_def import CredDef


class Credential:
    @abstractmethod
    def __init__(self, *args):
        pass


class AttribType:
    @abstractmethod
    def __init__(self, name: str, encode: bool):
        pass


class AttribDef:
    @abstractmethod
    def __init__(self, name, attrTypes):
        pass


class Attribs:
    @abstractmethod
    def __init__(self, credType: AttribDef, **vals):
        pass


class AttrRepo:
    @abstractmethod
    def getAttributes(self, proverId):
        pass

    @abstractmethod
    def addAttributes(self, proverId, attributes:Attribs):
        pass


class InMemoryAttrRepo(AttrRepo):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def getAttributes(self, proverId):
        pass

    @abstractmethod
    def addAttributes(self, proverId, attributes:Attribs):
        pass


class Issuer:

    @abstractmethod
    def __init__(self, id, attributeRepo: AttrRepo=None):
        pass

    @abstractmethod
    def addNewCredDef(self, **kwargs) -> CredDef:
        pass

    @abstractmethod
    def getCredDef(self, *args)-> CredDef:
        pass

    @abstractmethod
    def createCred(self, proverId, name, version, U):
        pass

    def initAttrRepo(self, attributeRepo: AttrRepo):
        pass

    def getAttributes(self, proverId) -> str:
        pass

    def addAttributes(self, proverId, attributes):
        pass
