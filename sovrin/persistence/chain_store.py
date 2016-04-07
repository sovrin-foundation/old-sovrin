from abc import abstractmethod

from sovrin.common.txn import TARGET_NYM, TXN_TYPE, ADD_NYM, ROLE, ORIGIN, USER


class ChainStore:
    # TODO super inefficient! we need to create a queryable data model
    # against the transaction log

    def getAddNymTxn(self, nym):
        for txnId, result in self.getAllTxn().items():
            if nym == result[TARGET_NYM]:
                if self.isAddNymTxn(result):
                    return result
        return None

    def getRole(self, nym):
        txn = self.getAddNymTxn(nym)
        return (txn[ROLE] if ROLE in txn else USER) if txn else None

    def getSponsorFor(self, nym):
        txn = self.getAddNymTxn(nym)
        return txn[ORIGIN] if txn and ORIGIN in txn else None

    @staticmethod
    def isAddNymTxn(result):
        return result[TXN_TYPE] == ADD_NYM

    def hasNym(self, nym):
        for txnId, result in self.getAllTxn().items():
            if nym == result[TARGET_NYM]:
                return True
        else:
            return False
