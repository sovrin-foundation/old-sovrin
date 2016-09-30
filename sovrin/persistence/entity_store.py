from abc import abstractmethod


class EntityStore:
    @abstractmethod
    def add(self, name: str, entity):
        pass

    @abstractmethod
    def get(self, name: str):
        pass
