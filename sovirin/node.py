from _sha256 import sha256
from typing import Dict, Iterable, Any
import asyncio

from plenum.common.request_types import Reply, Request
from plenum.common.stacked import HA
from plenum.server.client_authn import ClientAuthNr
from plenum.server.node import Node as PlenumNode
from plenum.server.primary_decider import PrimaryDecider
from plenum.storage.storage import Storage

from sovirin.txn import getGenesisTxns


class Node(PlenumNode):
    def __init__(self,
                 name: str,
                 nodeRegistry: Dict[str, HA],
                 clientAuthNr: ClientAuthNr=None,
                 ha: HA=None,
                 cliname: str=None,
                 cliha: HA=None,
                 basedirpath: str=None,
                 primaryDecider: PrimaryDecider = None,
                 opVerifiers: Iterable[Any]=None,
                 storage: Storage=None):

        super().__init__(name,
                         nodeRegistry,
                         clientAuthNr,
                         ha,
                         cliname,
                         cliha,
                         basedirpath,
                         primaryDecider,
                         opVerifiers,
                         storage)

        # Adding genesis transactions
        for idx, txn in enumerate(getGenesisTxns()):
            reply = Reply(0, idx, txn)
            asyncio.ensure_future(self.txnStore.insertTxn("", reply,
                                                          txn["txnId"]))

    def generateReply(self, viewNo: int, req: Request):
        operation = req.operation
        txnId = sha256("{}{}".format(req.clientId, req.reqId).
                       encode('utf-8')).hexdigest()
        result = {"txnId": txnId}
        return Reply(viewNo,
                      req.reqId,
                      result)
