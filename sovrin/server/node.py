import asyncio
from _sha256 import sha256

from plenum.common.exceptions import InvalidClientRequest, \
    UnauthorizedClientRequest
from plenum.common.request_types import Reply, Request
from plenum.server.node import Node as PlenumNode

from sovrin.common.txn import getGenesisTxns, TXN_TYPE, \
    TARGET_NYM, allOpKeys, validTxnTypes, ADD_ATTR, SPONSOR, ADD_NYM, ROLE, \
    STEWARD, ORIGIN, USER, NYM


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

    def checkValidOperation(self, clientId, reqId, msg):
        self.checkValidSovrinOperation(clientId, reqId, msg)
        super().checkValidOperation(clientId, reqId, msg)

    def checkValidSovrinOperation(self, clientId, reqId, msg):
        for k in msg.keys():
            if k not in allOpKeys:
                raise InvalidClientRequest(clientId, reqId,
                                           'invalid attribute "{}"'.format(k))

        if msg[TXN_TYPE] not in validTxnTypes:
            raise InvalidClientRequest(clientId, reqId, 'invalid {}: {}'.
                                       format(TXN_TYPE, msg[TXN_TYPE]))

        if msg[TXN_TYPE] == ADD_ATTR:
            if TARGET_NYM not in msg:
                raise InvalidClientRequest(clientId, reqId,
                                           '{} operation requires {} attribute'.
                                           format(ADD_ATTR, TARGET_NYM))

    async def checkRequestAuthorized(self, request: Request):
        op = request.operation
        typ = op[TXN_TYPE]
        role = op.get(ROLE, None)
        if typ == ADD_NYM:
            if role == SPONSOR:
                if not self.isSteward(op[ORIGIN]):
                    raise UnauthorizedClientRequest(request.clientId,
                                                    request.reqId,
                                                    "Only stewards can add sponsors")

            if role == USER:
                if not (self.isSteward(op[ORIGIN]) or self.isSponsor(op[ORIGIN])):
                    raise UnauthorizedClientRequest(request.clientId,
                                                    request.reqId,
                                                    "Only stewards or sponsors can "
                                                    "add sponsors")

    def isSteward(self, nym):
        for txnId, result in self.txnStore.getAllTxn().items():
            if nym == result[NYM]:
                if self.isAddNymTxn(result) and self.isRoleSteward(result):
                    return True

        return False

    def isSponsor(self, nym):
        for txnId, result in self.txnStore.getAllTxn().items():
            if nym == result[NYM]:
                if self.isAddNymTxn(result) and self.isRoleSponsor(result):
                    return True

        return False

    # TODO: Should be inside transaction store
    @staticmethod
    def isAddNymTxn(result):
        return TXN_TYPE in result and result[TXN_TYPE] == ADD_NYM

    # TODO: Should be inside transaction store
    @staticmethod
    def isRoleSteward(result):
        return ROLE in result and result[ROLE] == STEWARD

    # TODO: Should be inside transaction store
    @staticmethod
    def isRoleSponsor(result):
        return ROLE in result and result[ROLE] == SPONSOR
