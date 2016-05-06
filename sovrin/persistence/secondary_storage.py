from ledger.immutable_store.store import F
from plenum.common.txn import TXN_TYPE
from plenum.common.types import Reply
from plenum.persistence.secondary_storage import SecondaryStorage as PlenumSS
from sovrin.common.txn import ADD_NYM


class SecondaryStorage(PlenumSS):

    async def getReply(self, identifier, reqId, **kwargs):
        txn = self._txnStore.getTxn(identifier, reqId, kwargs)
        serial_no = txn.serialNo
        tree = self._primaryStorage.tree
        rootHash = tree.merkle_tree_hash(serial_no)
        auditPath = tree.inclusion_proof(0, serial_no)
        result = txn.update({
            F.rootHash.name: rootHash,
            F.auditPath.name: auditPath
        })
        return Reply(result)

    def getReplies(self, *txnIds, serialNo=None):
        txnData = self._txnStore.getRepliesForTxnIds(*txnIds, serialNo)
        tree = self._primaryStorage.tree
        for seqNo in txnData:
            rootHash = tree.merkle_tree_hash(serialNo)
            auditPath = tree.inclusion_proof(0, serialNo)
            merkleProof = {
                F.rootHash.name: rootHash,
                F.auditPath.name: auditPath
            }
            txnData[seqNo].update(merkleProof)
        return txnData

    def getAddNymTxn(self, nym):
        return self._txnStore.getAddNymTxn(nym)

    def getRole(self, nym):
        return self._txnStore.getRole(nym)

    def getSponsorFor(self, nym):
        return self._txnStore.getSponsorFor(nym)

    @staticmethod
    def isAddNymTxn(result):
        return result[TXN_TYPE] == ADD_NYM

    def hasNym(self, nym) -> bool:
        return self._txnStore.hasNym(nym)

