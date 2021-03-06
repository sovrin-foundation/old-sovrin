from typing import Dict

from plenum.common.txn import STEWARD
from plenum.common.types import Identifier

from sovrin.common.identity import Identity
from sovrin.server.auth import Authoriser


class Sponsoring:
    """
    Mixin to add sponsoring behaviors to a Wallet
    """

    def __init__(self):
        self._sponsored = {}  # type: Dict[Identifier, Identity]

    def addSponsoredIdentity(self, idy: Identity):
        if idy.role and not Authoriser.isValidRole(idy.role ):
            raise AttributeError("invalid role: {}".format(idy.role))
        if idy.identifier in self._sponsored:
            del self._sponsored[idy.identifier]
        self._sponsored[idy.identifier] = idy
        self._sendIdReq(idy)

    def _sendIdReq(self, idy):
        req = idy.ledgerRequest()
        if req:
            if not req.identifier:
                req.identifier = self.defaultId
            self.pendRequest(req, idy.identifier)
        return len(self._pending)

    def updateSponsoredIdentity(self, idy):
        storedId = self._sponsored.get(idy.identifier)
        if storedId:
            storedId.seqNo = None
        self._sendIdReq(idy)

    def getSponsoredIdentity(self, idr):
        return self._sponsored.get(idr)
