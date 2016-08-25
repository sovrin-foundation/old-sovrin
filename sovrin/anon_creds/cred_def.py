from abc import abstractmethod, abstractproperty
from enum import IntEnum, Enum


class SerFmt(Enum):
    default = 1
    py3Int = 2
    base58 = 3

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
    def getCryptoInteger(cls, val):
        pass