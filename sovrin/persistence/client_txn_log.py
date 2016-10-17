from typing import List

from plenum.common.txn import TXN_TYPE
from plenum.common.util import updateFieldsWithSeqNo
from plenum.persistence.client_txn_log import ClientTxnLog as PClientTxnLog

from sovrin.common.txn import getTxnOrderedFields


class ClientTxnLog(PClientTxnLog):

    @property
    def txnFieldOrdering(self):
        fields = getTxnOrderedFields()
        return updateFieldsWithSeqNo(fields)

    def getTxnsByType(self, txnType: str) -> List:
        txns = []
        for val in self.transactionLog.iterator(includeKey=False,
                                                includeValue=True):
            txn = self.serializer.deserialize(val, fields=self.txnFieldOrdering)
            if txn.get(TXN_TYPE) == txnType:
                txns.append(txn)
        return txns
