from abc import abstractmethod
from typing import Dict


class CredDefStore:
    def addCredDef(self, name: str, version: str, dest: str, type: str, ip: str,
                     port: int, keys: Dict):
        pass

    @abstractmethod
    def getCredDef(self, name: str, version: str, dest: str = None):
        pass
