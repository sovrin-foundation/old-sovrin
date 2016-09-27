from typing import Dict, Callable, Tuple

from plenum.common.error import fault
from plenum.common.exceptions import RemoteNotFound
from plenum.common.motor import Motor
from plenum.common.startable import Status
from plenum.common.types import Identifier
from sovrin.agent.agent_net import AgentNet
from sovrin.agent.endpoint import Endpoint
from sovrin.client.client import Client
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.identity import Identity


class Agent(Motor, AgentNet):
    def __init__(self,
                 name: str,
                 basedirpath: str,
                 client: Client=None,
                 port: int=None):
        Motor.__init__(self)
        self._name = name

        AgentNet.__init__(self,
                          name=self._name.replace(" ", ""),
                          port=port,
                          basedirpath=basedirpath,
                          msgHandler=self.handleEndpointMessage)

        # Client used to connect to Sovrin and forward on owner's txns
        self.client = client

        # known identifiers of this agent's owner
        self.ownerIdentifiers = {}  # type: Dict[Identifier, Identity]

    def name(self):
        pass

    async def prod(self, limit) -> int:
        c = 0
        if self.get_status() == Status.starting:
            self.status = Status.started
            c += 1
        if self.client:
            c += await self.client.prod(limit)
        if self.endpoint:
            c += await self.endpoint.service(limit)
        return c

    def start(self, loop):
        super().start(loop)
        if self.client:
            self.client.start(loop)
        if self.endpoint:
            self.endpoint.start()

    def _statusChanged(self, old, new):
        pass

    def onStopping(self, *args, **kwargs):
        pass

    def connect(self, network: str):
        """
        Uses the client to connect to Sovrin
        :param network: (test|live)
        :return:
        """
        raise NotImplementedError

    def syncKeys(self):
        """
        Iterates through ownerIdentifiers and ensures the keys are correct
        according to Sovrin. Updates the updated
        :return:
        """
        raise NotImplementedError

    def handleOwnerRequest(self, request):
        """
        Consumes an owner request, verifies it's authentic (by checking against
        synced owner identifiers' keys), and handles it.
        :param request:
        :return:
        """
        raise NotImplementedError

    def handleEndpointMessage(self, msg):
        pass

    def sendMessage(self, msg, destName: str=None, destHa: Tuple=None):
        try:
            remote = self.endpoint.getRemote(name=destName, ha=destHa)
        except RemoteNotFound as ex:
            fault(ex, "Do not know {} {}".format(destName, destHa))
            return
        self.endpoint.transmit(msg, remote.uid)

    def connectTo(self, ha):
        self.endpoint.connectTo(ha)


class WalletedAgent(Agent):
    """
    An agent with a self-contained wallet.

    Normally, other logic acts upon a remote agent. That other logic holds keys
    and signs messages and transactions that the Agent then forwards. In this
    case, the agent holds a wallet.
    """
    def __init__(self,
                 name: str,
                 basedirpath: str,
                 client: Client=None,
                 wallet: Wallet=None,
                 port: int=None):
        super().__init__(name, basedirpath, client, port)
        self._wallet = wallet or Wallet(name)

    @property
    def wallet(self):
        return self._wallet

    @wallet.setter
    def wallet(self, wallet):
        self._wallet = wallet
