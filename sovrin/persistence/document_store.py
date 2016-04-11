import pyorient

from plenum.common.util import getlogger
from sovrin.persistence.orientdb_store import OrientDbStore

logger = getlogger()


class DocumentStore(OrientDbStore):
    def __init__(self, user, password, dbName, host="localhost", port=2424,
                 storageType=pyorient.STORAGE_TYPE_PLOCAL):
        super().__init__(user, password, dbName, host=host, port=port,
                         storageType=storageType)

    def createDb(self, dbName, storageType):
        logger.debug("Creating Document DB {}".format(dbName))
        self.client.db_create(dbName, pyorient.DB_TYPE_DOCUMENT, storageType)
