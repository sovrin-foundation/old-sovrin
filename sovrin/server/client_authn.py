from libnacl.encode import base64_decode

from plenum.server.client_authn import NaclAuthNr
from sovrin.persistence.chain_store import ChainStore


class TxnBasedAuthNr(NaclAuthNr):
    """
    Transaction-based client authenticator.
    """
    def __init__(self, storage: ChainStore):
        self.storage = storage

    def addClient(self, identifier, verkey):
        raise RuntimeError('Add verification keys through the ADDNYM txn')

    def getVerkey(self, identifier):
        txn = self.storage.getAddNymTxn(identifier)
        if not txn:
            raise KeyError('unknown identifier')
        return base64_decode(identifier.encode())
