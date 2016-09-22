from typing import Dict

from plenum.common.motor import Motor
from plenum.common.startable import Status
from plenum.common.types import Identifier
from sovrin.agent.agent_net import AgentNet
from sovrin.client.client import Client
from sovrin.common.identity import Identity


class Agent(Motor, AgentNet):
    def __init__(self, name: str="agent1", client: Client=None):
        super().__init__()
        self._name = name

        # Client used to connect to Sovrin and forward on owner's txns
        self.client = client

        # known identifiers of this agent's owner
        self.ownerIdentifiers = {}  # type: Dict[Identifier, Identity]

    def name(self):
        pass

    async def prod(self, limit) -> int:
        if self.get_status() == Status.starting:
            self.status = Status.started
            return 1
        return 0

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
