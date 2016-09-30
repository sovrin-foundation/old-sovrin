from _sha256 import sha256
from copy import deepcopy

from libnacl.encode import base64_decode
from plenum.common.txn import TXN_TYPE, RAW, ENC, HASH

from plenum.server.client_authn import NaclAuthNr
from sovrin.common.txn import ATTRIB
from sovrin.persistence.identity_graph import IdentityGraph


class TxnBasedAuthNr(NaclAuthNr):
    """
    Transaction-based client authenticator.
    """
    def __init__(self, storage: IdentityGraph):
        self.storage = storage

    def serializeForSig(self, msg):
        if msg["operation"].get(TXN_TYPE) == ATTRIB:
            msgCopy = deepcopy(msg)
            keyName = {RAW, ENC, HASH}.intersection(
                set(msgCopy["operation"].keys())).pop()
            msgCopy["operation"][keyName] = sha256(msgCopy["operation"][keyName]
                                                   .encode()).hexdigest()
            return super().serializeForSig(msgCopy)
        else:
            return super().serializeForSig(msg)

    def addClient(self, identifier, verkey, role=None):
        raise RuntimeError('Add verification keys through the ADDNYM txn')

    def getVerkey(self, identifier):
        txn = self.storage.getAddNymTxn(identifier)
        if not txn:
            raise KeyError('unknown identifier')
        return base64_decode(identifier.encode())
