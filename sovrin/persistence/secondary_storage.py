import base64

from ledger.util import F
from plenum.common.txn import TXN_TYPE
from plenum.common.types import Reply
from plenum.persistence.secondary_storage import SecondaryStorage as PlenumSS
from sovrin.common.txn import NYM


class SecondaryStorage(PlenumSS):

    # def storeReply(self, reply: Reply):
    #     return self._txnStore.storeReply(reply)

    def _merkleInfo(self, seqNo):
        tree = self._primaryStorage.tree
        rootHash = tree.merkle_tree_hash(0, int(seqNo))
        auditPath = tree.inclusion_proof(0, int(seqNo))
        return {
            F.rootHash.name: base64.b64encode(rootHash).decode(),
            F.auditPath.name: [base64.b64encode(h).decode() for h in auditPath]
        }

    async def getReply(self, identifier, reqId, **kwargs):
        txn = self._txnStore.getTxn(identifier, reqId, **kwargs)
        if txn:
            txn.update(self._merkleInfo(txn.seqNo))
            return Reply(txn)

    # def _addMerkleInfo(self, txn):
    #     seqNo = txn.seqNo
    #     tree = self._primaryStorage.tree
    #     rootHash = tree.merkle_tree_hash(seqNo)
    #     auditPath = tree.inclusion_proof(0, seqNo)
    #     result = txn.update({
    #         F.rootHash.name: rootHash,
    #         F.auditPath.name: auditPath
    #     })
    #     return Reply(result)

    def getReplies(self, *txnIds, seqNo=None):
        txnData = self._txnStore.getResultForTxnIds(*txnIds, seqNo=seqNo)
        if not txnData:
            return txnData
        else:
            for seqNo in txnData:
                txnData[seqNo].update(self._merkleInfo(seqNo))
            return txnData

    def getAddNymTxn(self, nym):
        return self._txnStore.getAddNymTxn(nym)

    def getRole(self, nym):
        return self._txnStore.getRole(nym)

    def getSponsorFor(self, nym):
        return self._txnStore.getSponsorFor(nym)

    @staticmethod
    def isAddNymTxn(result):
        return result[TXN_TYPE] == NYM

    def hasNym(self, nym) -> bool:
        return self._txnStore.hasNym(nym)
