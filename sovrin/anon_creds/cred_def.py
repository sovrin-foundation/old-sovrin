from abc import abstractmethod, abstractproperty
from enum import IntEnum, Enum


class SerFmt(Enum):
    default = 1
    py3Int = 2
    base58 = 3

class CredDefPublicKey:
    @abstractmethod
    def __init__(self, *args):
        pass


class CredDef:
    @abstractmethod
    def __init__(self,
                 attrNames,
                 name=None, version=None,
                 p_prime=None, q_prime=None,
                 ip=None, port=None):
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
    def get(self, serFmt: SerFmt):
        pass