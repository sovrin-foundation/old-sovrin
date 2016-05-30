from ledger.stores.text_file_store import TextFileStore
from sovrin.persistence.entity_store import EntityStore


class EntityFileStore(EntityStore):
    def __init__(self, name: str, dataDir: str):
        self._db = TextFileStore(dbName=name, dbDir=dataDir)

    def add(self, name: str, entity):
        self._db.put(name, entity)

    def get(self, name: str):
        return self._db.get(name)