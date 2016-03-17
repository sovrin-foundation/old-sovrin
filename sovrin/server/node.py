import asyncio
from _sha256 import sha256

from plenum.common.exceptions import InvalidClientRequest, \
    UnauthorizedClientRequest
from plenum.common.request_types import Reply, Request
from plenum.server.node import Node as PlenumNode

from sovrin.common.txn import getGenesisTxns, TXN_TYPE, \
    TARGET_NYM, allOpKeys, validTxnTypes, ADD_ATTR, SPONSOR, ADD_NYM, ROLE, \
    STEWARD, ORIGIN, USER


class Node(PlenumNode):
    def addGenesisTxns(self, genTxns=None):
        if self.txnStore.size() == 0:
            gt = genTxns or getGenesisTxns()
            for idx, txn in enumerate(gt):
                reply = Reply(0, idx, txn)
                asyncio.ensure_future(
                    self.txnStore.append("", reply, txn["txnId"]))

    def generateReply(self, viewNo: int, req: Request):
        operation = req.operation
        txnId = sha256(
            "{}{}".format(req.identifier, req.reqId).encode()).hexdigest()
        result = {"txnId": txnId}
        # TODO: Just for the time being. Remove ASAP
        result.update(operation)
        return Reply(viewNo,
                     req.reqId,
                     result)

    def checkValidOperation(self, identifier, reqId, msg):
        self.checkValidSovrinOperation(identifier, reqId, msg)
        super().checkValidOperation(identifier, reqId, msg)

    @staticmethod
    def checkValidSovrinOperation(identifier, reqId, msg):
        for k in msg.keys():
            if k not in allOpKeys:
                raise InvalidClientRequest(identifier, reqId,
                                           'invalid attribute "{}"'.format(k))

        if msg[TXN_TYPE] not in validTxnTypes:
            raise InvalidClientRequest(identifier, reqId, 'invalid {}: {}'.
                                       format(TXN_TYPE, msg[TXN_TYPE]))

        if msg[TXN_TYPE] == ADD_ATTR:
            if TARGET_NYM not in msg:
                raise InvalidClientRequest(identifier, reqId,
                                           '{} operation requires {} attribute'.
                                           format(ADD_ATTR, TARGET_NYM))

    # TODO: DO not trust the ORIGIN in transaction
    async def checkRequestAuthorized(self, request: Request):
        op = request.operation
        typ = op[TXN_TYPE]
        allTxns = None

        def getAllTxns():
            allTxns = self.txnStore.getAllTxn()
            return allTxns

        if typ == ADD_NYM:
            role = op.get(ROLE, None)
            if role == SPONSOR:
                if not self.isSteward(op[ORIGIN], allTxns or getAllTxns()):
                    raise UnauthorizedClientRequest(
                        request.identifier,
                        request.reqId,
                        "Only stewards can add sponsors")

            if role == USER:
                if not (self.isSteward(op[ORIGIN], allTxns or getAllTxns()) or
                            self.isSponsor(op[ORIGIN], allTxns or getAllTxns())):
                    raise UnauthorizedClientRequest(
                        request.identifier,
                        request.reqId,
                        "Only stewards or sponsors can "
                        "add sponsors")

        elif typ == ADD_ATTR:
            if not self.isSponsorFor(op[ORIGIN], op[TARGET_NYM], allTxns or getAllTxns()):
                raise UnauthorizedClientRequest(
                        request.identifier,
                        request.reqId,
                        "Only user's sponsor can add attribute for that user"
                )

    def isSteward(self, nym, allTxns):
        for txnId, result in allTxns.items():
            if nym == result[TARGET_NYM]:
                if self.isAddNymTxn(result) and self.isRoleSteward(result):
                    return True

        return False

    def isSponsor(self, nym, allTxns):
        for txnId, result in allTxns.items():
            if nym == result[TARGET_NYM]:
                if self.isAddNymTxn(result) and self.isRoleSponsor(result):
                    return True

        return False

    def isSponsorFor(self, sponsorNym, forNym, allTxns):
        for txnId, result in allTxns.items():
            if result[TXN_TYPE] == ADD_NYM and forNym == result[TARGET_NYM] \
                    and result[ORIGIN] == sponsorNym and result[ROLE] == USER:
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
