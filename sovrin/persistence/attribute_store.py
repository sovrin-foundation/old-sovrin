from abc import abstractmethod, abstractproperty
from typing import Any, Optional


class AttributeStore:
    def addAttribute(self, name: str, val: Any, origin: str,
                     dest: Optional[str] = None, encKey: Optional[str] = None,
                     encType: Optional[str] = None, hashed: bool = False):
        pass

    @abstractmethod
    def getAttribute(self, name: str, dest: Optional[str] = None):
        pass

    @abstractproperty
    def attributes(self):
        pass
