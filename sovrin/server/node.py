import asyncio
from _sha256 import sha256

from plenum.common.exceptions import InvalidClientRequest
from plenum.common.request_types import Reply, Request
from plenum.server.node import Node as PlenumNode

from sovrin.common.txn import getGenesisTxns, TXN_TYPE, \
    TARGET_NYM, allOpKeys, validTxnTypes, ADD_ATTR, SPONSOR, ADD_NYM, ROLE, \
    STEWARD, ORIGIN


class Node(PlenumNode):
    def addGenesisTxns(self, genTxns=None):
        if self.txnStore.size() == 0:
            gt = genTxns or getGenesisTxns()
            for idx, txn in enumerate(gt):
                reply = Reply(0, idx, txn)
                asyncio.ensure_future(
                    self.txnStore.insertTxn("", reply, txn["txnId"]))

    def generateReply(self, viewNo: int, req: Request):
        operation = req.operation
        txnId = sha256(
            "{}{}".format(req.clientId, req.reqId).encode()).hexdigest()
        result = {"txnId": txnId}
        # TODO: Just for the time being. Remove ASAP
        result.update(operation)
        return Reply(viewNo,
                      req.reqId,
                      result)

    def checkValidOperation(self, msg):
        self.checkValidSovrinOperation(msg)
        super().checkValidOperation(msg)

    def checkValidSovrinOperation(self, msg):
        for k in msg.keys():
            if k not in allOpKeys:
                raise InvalidClientRequest('invalid attribute "{}"'.format(k))

        if msg[TXN_TYPE] not in validTxnTypes:
            raise InvalidClientRequest('invalid {}: {}'.
                                       format(TXN_TYPE, msg[TXN_TYPE]))

        if msg[TXN_TYPE] == ADD_ATTR:
            if TARGET_NYM not in msg:
                raise InvalidClientRequest('{} operation requires {} attribute'.
                                           format(ADD_ATTR, TARGET_NYM))

    async def checkRequestAuthorized(self, request):
        op = request.operation
        typ = op[TXN_TYPE]
        role = op.get(ROLE, None)
        if typ == ADD_NYM and role == SPONSOR:
            if not self.IsSteward(op[ORIGIN]):
                raise InvalidClientRequest("Only stewards can add sponsors")

    def IsSteward(self, nym):
        for txnId, result in self.txnStore.getAllTxn().items():
            if self.isAddNymTxn(result) and self.isRoleSteward(result):
                return True

        return False

    # TODO: Should go to transaction store
    @staticmethod
    def isAddNymTxn(result):
        return TXN_TYPE in result and result [TXN_TYPE] == ADD_NYM

    # TODO: Should go to transaction store
    @staticmethod
    def isRoleSteward(result):
        return ROLE in result and result[ROLE] == STEWARD
