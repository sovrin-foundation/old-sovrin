import asyncio

import time
from _sha256 import sha256

import pyorient

from plenum.common.exceptions import InvalidClientRequest, \
    UnauthorizedClientRequest
from plenum.common.request_types import Reply, Request, RequestAck
from plenum.server.node import Node as PlenumNode
from sovrin.common.has_file_storage import HasFileStorage

from sovrin.common.txn import getGenesisTxns, TXN_TYPE, \
    TARGET_NYM, allOpKeys, validTxnTypes, ADD_ATTR, SPONSOR, ADD_NYM, ROLE, \
    STEWARD, USER, GET_ATTR, DISCLOSE, ORIGIN, DATA, NONCE, GET_NYM, TXN_ID, \
    TXN_TIME, ATTRIBUTES
from sovrin.persistence.chain_store import ChainStore
from sovrin.persistence.graph_storage import GraphStorage
from sovrin.persistence.ledger_chain_store import LedgerChainStore
from sovrin.server.client_authn import TxnBasedAuthNr
from sovrin.common.util import getConfig


class Node(PlenumNode, HasFileStorage):

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

        self.dataDir = "data/nodes"
        if not storage:
            HasFileStorage.__init__(self, name, baseDir=basedirpath,
                                    dataDir=self.dataDir)
            storage = LedgerChainStore(self.getDataLocation())

        self.graphStorage = self.getGraphStorage(name)

        super().__init__(name=name,
                         nodeRegistry=nodeRegistry,
                         clientAuthNr=clientAuthNr,
                         ha=ha,
                         cliname=cliname,
                         cliha=cliha,
                         basedirpath=basedirpath,
                         primaryDecider=primaryDecider,
                         opVerifiers=opVerifiers,
                         storage=storage)

    def getGraphStorage(self, name):
        config = getConfig()
        return GraphStorage(user=config.GraphDB["user"],
                            password=config.GraphDB["password"],
                            dbName=name,
                            storageType=pyorient.STORAGE_TYPE_PLOCAL)

    # TODO: Should adding of genesis transactions be part of start method
    def addGenesisTxns(self, genTxns=None):
        if self.txnStore.size == 0:
            gt = genTxns or getGenesisTxns()
            for idx, txn in enumerate(gt):
                reply = Reply(0, idx, txn)
                asyncio.ensure_future(
                    self.txnStore.append("", reply, txn[TXN_ID]))
                if txn[TXN_TYPE] == ADD_NYM:
                    self.addNymToGraph(txn)
                # Till now we just have ADD_NYM in genesis transaction.

    def generateReply(self, viewNo: int, ppTime: float, req: Request):
        operation = req.operation
        txnId = sha256(
            "{}{}".format(req.identifier, req.reqId).encode()).hexdigest()
        result = {TXN_ID: txnId, TXN_TIME: ppTime}
        # if operation[TXN_TYPE] == GET_ATTR:
        #     # TODO: Very inefficient, queries all transactions and looks for the
        #     # DISCLOSE for the clients and returns all. We probably change the
        #     # transaction schema or have some way to zero in on the DISCLOSE for
        #     # the attribute that is being looked for
        #     attrs = []
        #     for txn in self.txnStore.getAllTxn().values():
        #         if txn.get(TARGET_NYM, None) == req.identifier and txn[TXN_TYPE] == \
        #                 DISCLOSE:
        #             attrs.append({DATA: txn[DATA], NONCE: txn[NONCE]})
        #     if attrs:
        #         result[ATTRIBUTES] = attrs
        # TODO: Just for the time being. Remove ASAP
        result.update(operation)
        if operation[TXN_TYPE] == ADD_NYM:
            self.addNymToGraph(result)
        elif operation[TXN_TYPE] == ADD_ATTR:
            self.graphStorage.addAttribute(frm=operation[ORIGIN],
                                           to=operation[TARGET_NYM],
                                           data=operation[DATA],
                                           txnId=txnId)
        return Reply(viewNo,
                     req.reqId,
                     result)

    def addNymToGraph(self, txn):
        if ROLE not in txn or txn[ROLE] == USER:
            self.graphStorage.addUser(txn[TXN_ID], txn[TARGET_NYM], txn[ORIGIN])
        elif txn[ROLE] == SPONSOR:
            self.graphStorage.addSponsor(txn[TXN_ID], txn[TARGET_NYM], txn[ORIGIN])
        elif txn[ROLE] == STEWARD:
            self.graphStorage.addSteward(txn[TXN_ID], txn[TARGET_NYM], txn.get(ORIGIN))
        else:
            raise ValueError("Unknown role for nym, cannot add nym to graph")

    def checkValidOperation(self, identifier, reqId, msg):
        self.checkValidSovrinOperation(identifier, reqId, msg)
        super().checkValidOperation(identifier, reqId, msg)

    def checkValidSovrinOperation(self, identifier, reqId, msg):
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
            if not self.graphStorage.hasNym(msg[TARGET_NYM]):
                raise InvalidClientRequest(identifier, reqId,
                                           '{} should be added before adding '
                                           'attribute for it'.
                                           format(TARGET_NYM))

        if msg[TXN_TYPE] == ADD_NYM:
            if self.graphStorage.hasNym(msg[TARGET_NYM]):
                raise InvalidClientRequest(identifier, reqId,
                                           "{} is already present".
                                           format(msg[TARGET_NYM]))

    authorizedAdders = {
        USER: (STEWARD, SPONSOR),
        SPONSOR: (STEWARD,)
    }

    async def checkRequestAuthorized(self, request: Request):
        op = request.operation
        typ = op[TXN_TYPE]

        s = self.graphStorage  # type: GraphStorage

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
        return TxnBasedAuthNr(self.graphStorage)

    async def processRequest(self, request: Request, frm: str):
        if request.operation[TXN_TYPE] == GET_NYM:
            self.transmitToClient(RequestAck(request.reqId), frm)
            nym = request.operation[TARGET_NYM]
            txn = self.graphStorage.getAddNymTxn(nym)
            txnId = sha256("{}{}".format(request.identifier, request.reqId).
                           encode()).hexdigest()
            result = {DATA: txn.get(TXN_ID) if txn else None,
                      TXN_ID: txnId,
                      TXN_TIME: time.time()
                      }
            result.update(request.operation)
            self.transmitToClient(Reply(self.viewNo, request.reqId, result), frm)
        else:
            await super().processRequest(request, frm)
