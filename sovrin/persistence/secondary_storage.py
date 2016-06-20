import base64

from ledger.util import F
from plenum.common.txn import TXN_TYPE
from plenum.common.types import Reply
from plenum.persistence.secondary_storage import SecondaryStorage as PlenumSS
from sovrin.common.txn import NYM


class SecondaryStorage(PlenumSS):

    def storeReply(self, reply: Reply):
        return self._txnStore.storeReply(reply)

    async def getReply(self, identifier, reqId, **kwargs):
        txn = self._txnStore.getTxn(identifier, reqId, **kwargs)
        return txn and self._addMerkleInfo(txn)

    def _addMerkleInfo(self, txn):
        seqNo = txn.seqNo
        tree = self._primaryStorage.tree
        rootHash = tree.merkle_tree_hash(seqNo)
        auditPath = tree.inclusion_proof(0, seqNo)
        result = txn.update({
            F.rootHash.name: rootHash,
            F.auditPath.name: auditPath
        })
        return Reply(result)

    def getReplies(self, *txnIds, seqNo=None):
        txnData = self._txnStore.getRepliesForTxnIds(*txnIds, seqNo)
        if not txnData:
            return txnData
        else:
            tree = self._primaryStorage.tree
            for seqNo in txnData:
                rootHash = tree.merkle_tree_hash(0, int(seqNo))
                auditPath = tree.inclusion_proof(0, int(seqNo))
                merkleProof = {
                    F.rootHash.name: base64.b64encode(rootHash).decode(),
                    F.auditPath.name: [base64.b64encode(h).decode()
                                       for h in auditPath]
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
        return result[TXN_TYPE] == NYM

    def hasNym(self, nym) -> bool:
        return self._txnStore.hasNym(nym)
