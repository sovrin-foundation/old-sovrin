from typing import Mapping, List

from plenum.client.client import Client as PlenumClient
from plenum.common.request_types import OP_FIELD_NAME, Request
from plenum.common.txn import REQACK, REPLY
from plenum.common.util import getlogger

from sovrin.client.client_storage import ClientStorage


logger = getlogger()


class Client(PlenumClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.storage = self.getStorage()
        self.lastReqId = self.storage.getLastReqId()

    def getStorage(self):
        return ClientStorage(self.clientId)

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
            self.storage.addReply(msg['reqId'], sender, result)
        else:
            logger.debug("Invalid op message {}".format(msg))
