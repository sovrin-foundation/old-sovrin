from typing import Callable, Any, List, Dict

from plenum.common.stacked import SimpleStack
from plenum.common.types import HA
from plenum.common.util import getlogger, randomString
from raet.raeting import AutoMode
from sovrin.agent.agent_net import AgentNet

logger = getlogger()


class Endpoint(AgentNet, SimpleStack):
    def __init__(self, port: int, msgHandler: Callable,
                 name: str=None):
        stackParams = {
            "name": name or randomString(8),
            "ha": HA("127.0.0.1", port),
            "main": True,
            "auto": AutoMode.always,
            "mutable": "mutable",
        }
        SimpleStack.__init__(self, stackParams, self.baseMsgHandler)
        self.msgHandler = msgHandler

    def transmitToClient(self, msg: Any, remoteName: str):
        """
        Transmit the specified message to the remote client specified by
         `remoteName`.
        :param msg: a message
        :param remoteName: the name of the remote
        """
        # At this time, nodes are not signing messages to clients, beyond what
        # happens inherently with RAET
        payload = self.prepForSending(msg)
        try:
            self.send(payload, remoteName)
        except Exception as ex:
            logger.error("{} unable to send message {} to client {}; "
                         "Exception: {}".format(self.name, msg, remoteName,
                                               ex.__repr__()))

    def transmitToClients(self, msg: Any, remoteNames: List[str]):
        for nm in remoteNames:
            self.transmitToClient(msg, nm)

    # TODO: Rename method
    def baseMsgHandler(self, msg):
        logger.debug("Got {}".format(msg))
        self.msgHandler(msg)

