from abc import abstractmethod, abstractproperty
from enum import Enum


class CredDefPublicKey:
    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass


class CredDef:
    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    @abstractproperty
    def name(self) -> str:
        pass

    @abstractproperty
    def version(self) -> str:
        pass

    @abstractproperty
    def serializedSK(self) -> str:
        pass

    @abstractmethod
    def get(self, *args, **kwargs):
        pass

    @abstractmethod
    def getPk(*args, **kwargs):
        pass

    @abstractmethod
    def getCryptoInteger(cls, *args, **kwargs):
        pass

    @abstractmethod
    def getStaticPPrime(cls, *args, **kwargs):
        pass

    @abstractmethod
    def getStaticQPrime(cls, *args, **kwargs):
        pass

    @abstractmethod
    def getEncodedAttrs(cls, *args, **kwargs):
        pass