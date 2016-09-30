from copy import deepcopy
from hashlib import sha256

from plenum.common.txn import TXN_TYPE, RAW, ENC, HASH
from plenum.common.types import Request as PRequest, OPERATION
from sovrin.common.txn import ATTRIB


class Request(PRequest):
    def getSigningState(self):
        """
        Special signing state where the the data for an attribute is hashed
        before signing
        :return: state to be used when signing
        """
        if self.operation.get(TXN_TYPE) == ATTRIB:
            d = deepcopy(super().getSigningState())
            op = d[OPERATION]
            keyName = {RAW, ENC, HASH}.intersection(set(op.keys())).pop()
            op[keyName] = sha256(op[keyName].encode()).hexdigest()
            return d
        return super().getSigningState()


