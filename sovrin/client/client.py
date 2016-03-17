from typing import Mapping, List, Any, Dict, Union, Tuple

import pickle
from plenum.client.client import Client as PlenumClient
from plenum.client.signer import Signer
from plenum.common.request_types import OP_FIELD_NAME, Request
from plenum.common.stacked import HA
from plenum.common.txn import REQACK, REPLY
from plenum.common.util import getlogger, getMaxFailures

from sovrin.client.client_storage import ClientStorage


logger = getlogger()


class Client(PlenumClient):
    def __init__(self,
                 name: str,
                 nodeReg: Dict[str, HA]=None,
                 ha: Union[HA, Tuple[str, int]]=None,
                 lastReqId: int = 0,
                 signer: Signer=None,
                 signers: Dict[str, Signer]=None,
                 basedirpath: str=None):
        super().__init__(name,
                         nodeReg,
                         ha,
                         lastReqId,
                         signer,
                         signers,
                         basedirpath)
        self.storage = self.getStorage()
        self.lastReqId = self.storage.getLastReqId()

    def getStorage(self):
        return ClientStorage(self.name)

    def submit(self, *operations: Mapping) -> List[Request]:
        requests = super().submit(*operations)
        for r in requests:
            self.storage.addRequest(r)
        return requests

    def handleOneNodeMsg(self, wrappedMsg) -> None:
        super().handleOneNodeMsg(wrappedMsg)
        msg, sender = wrappedMsg
        if OP_FIELD_NAME not in msg:
            logger.error("Op absent in message {}".format(msg))
        if msg[OP_FIELD_NAME] == REQACK:
            self.storage.addAck(msg['reqId'], sender)
        elif msg[OP_FIELD_NAME] == REPLY:
            result = msg['result']
            self.storage.addReply(msg['reqId'], sender, {'result': result})
        else:
            logger.debug("Invalid op message {}".format(msg))

    def getRepliesFromAllNodes(self, reqId: int):
        result = {k.split(b'-')[1].decode(): pickle.loads(v) for k,
                                                    v in self.storage.replyStore.iterator(prefix=str(reqId).encode())}
        return result

    def getTxnsByNym(self, nym: str):
        # TODO Implement this
        pass

    def getTxnsByAttribute(self, attrName: str, attrValue: Any=None):
        def cond(result):
            return attrName in result and (attrValue is None or attrValue ==
                                           result[attrName])

        return self.getTxnsByCondition(condition=cond)

    def getTxnsByCondition(self, condition):
        # TODO: This is very inefficient. For a starting point store have a
        # keyspace partition for storing a map of cryptonyms(or txn types or
        # which attribute of interest) to reqIds

        results = {}        # tpye: Dict[int, Tuple[Set[str], Any])
        for k, v in self.storage.replyStore.iterator():
            result = pickle.loads(v)['result']
            if condition(result):
                reqId, sender = k.split(b'-')
                reqId = int(reqId)
                sender = sender.decode()
                if reqId not in results:
                    results[reqId] = (set(), result)
                results[reqId][0].add(sender)
                # TODO: What about different nodes sending differnet replies?
                #  Need to pick reply which is given by f+1 nodes. Having
                # hashes to check for equality might be efficient

        f = getMaxFailures(len(self.nodeReg))
        return [val[1] for rid, val in results.items() if len(val[0]) > f]
