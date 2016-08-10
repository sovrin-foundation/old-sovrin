import base64

from ledger.util import F
from plenum.common.txn import TXN_TYPE
from plenum.common.types import Reply
from plenum.persistence.secondary_storage import SecondaryStorage as PlenumSS
from sovrin.common.txn import NYM


class SecondaryStorage(PlenumSS):

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
            txn.update(self._merkleInfo(txn.get(F.seqNo.name)))
            return Reply(txn)

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
