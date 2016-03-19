import asyncio
from _sha256 import sha256

from plenum.common.exceptions import InvalidClientRequest, \
    UnauthorizedClientRequest
from plenum.common.request_types import Reply, Request
from plenum.server.node import Node as PlenumNode

from sovrin.common.txn import getGenesisTxns, TXN_TYPE, \
    TARGET_NYM, allOpKeys, validTxnTypes, ADD_ATTR, SPONSOR, ADD_NYM, ROLE, \
    STEWARD, USER, GET_ATTR, DISCLOSE, ORIGIN, DATA, NONCE
from sovrin.persistence.chain_store import ChainStore
from sovrin.persistence.memory_chain_store import MemoryChainStore
from sovrin.server.client_authn import TxnBasedAuthNr


class Node(PlenumNode):

    def __init__(self,
                 name,
                 nodeRegistry,
                 clientAuthNr=None,
                 ha=None,
                 cliname=None,
                 cliha=None,
                 basedirpath=None,
                 primaryDecider=None,
                 opVerifiers=None,
                 storage=None):

        store = storage or MemoryChainStore()

        super().__init__(name=name,
                         nodeRegistry=nodeRegistry,
                         clientAuthNr=clientAuthNr,
                         ha=ha,
                         cliname=cliname,
                         cliha=cliha,
                         basedirpath=basedirpath,
                         primaryDecider=primaryDecider,
                         opVerifiers=opVerifiers,
                         storage=store)

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
        if operation[TXN_TYPE] == GET_ATTR:
            # TODO: Very inefficient, queries all transactions and looks for the
            # DISCLOSE for the clients and returns all. We probably change the
            # transaction schema or have some way to zero in on the DISCLOSE for
            # the attribute that is being looked for
            attrs = []
            for txn in self.txnStore.getAllTxn().values():
                if txn.get(TARGET_NYM, None) == req.identifier and txn[TXN_TYPE] == \
                        DISCLOSE:
                    attrs.append({DATA: txn[DATA], NONCE: txn[NONCE]})
            if attrs:
                result["attributes"] = attrs
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

    authorizedAdders = {
        USER: (STEWARD, SPONSOR),
        SPONSOR: (STEWARD,)
    }

    async def checkRequestAuthorized(self, request: Request):
        op = request.operation
        typ = op[TXN_TYPE]

        s = self.txnStore  # type: ChainStore

        origin = request.identifier
        originRole = s.getRole(origin)

        if typ == ADD_NYM:
            role = op.get(ROLE, USER)
            authorizedAdder = self.authorizedAdders[role]
            if originRole not in authorizedAdder:
                raise UnauthorizedClientRequest(
                    request.identifier,
                    request.reqId,
                    "{} cannot add {}".format(originRole, role))
        elif typ == ADD_ATTR:
            if not s.getSponsorFor(op[TARGET_NYM]) == origin:
                raise UnauthorizedClientRequest(
                        request.identifier,
                        request.reqId,
                        "Only user's sponsor can add attribute for that user")
        # TODO: Just for now. Later do something meaningful here
        elif typ in [DISCLOSE, GET_ATTR]:
            pass
        else:
            raise UnauthorizedClientRequest(
                    request.identifier,
                    request.reqId,
                    "Assuming no one is authorized for txn type {}".format(typ))

    def defaultAuthNr(self):
        return TxnBasedAuthNr(self.txnStore)
