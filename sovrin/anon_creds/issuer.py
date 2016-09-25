from abc import abstractmethod

from sovrin.anon_creds.cred_def import CredDef


class Credential:
    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass


class AttribType:
    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass


class Attribs:
    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def encoded(self):
        pass


class AttribDef:
    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def attribs(self, *args, **kwargs) -> Attribs:
        pass

    @abstractmethod
    def attribNames(self):
        pass


class AttrRepo:
    @abstractmethod
    def getAttributes(self, *args, **kwargs):
        pass

    @abstractmethod
    def addAttributes(self, *args, **kwargs):
        pass


class InMemoryAttrRepo(AttrRepo):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def getAttributes(self, *args, **kwargs):
        pass

    @abstractmethod
    def addAttributes(self, *args, **kwargs):
        pass


class Issuer:

    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def addNewCredDef(self, *args, **kwargs) -> CredDef:
        pass

    @abstractmethod
    def getCredDef(self, *args, **kwargs)-> CredDef:
        pass

    @abstractmethod
    def createCred(self, *args, **kwargs):
        pass
