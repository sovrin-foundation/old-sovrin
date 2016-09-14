from typing import Dict

from plenum.common.motor import Motor
from plenum.common.startable import Status
from sovrin.agent.agent_net import AgentNet
from sovrin.client.client import Client


Identifier = str


class SyncedKey:
    def __init__(self, verkey=None, last_synced=None, seqNo=None):

        # None indicates the identifier is a cryptonym
        self.verkey = verkey

        # timestamp for when the ledger was last checked for key replacement or
        # revocation
        self.last_synced = last_synced

        # seqence number of the latest key management transaction for this
        # identifier
        self.seqNo = seqNo


class Agent(Motor, AgentNet):
    def __init__(self, name: str="agent1", client: Client=None):
        super().__init__()
        self._name = name

        # Client used to connect to Sovrin and forward on owner's txns
        self.client = client

        # known identifiers of this agent's owner
        self.ownerIdentifiers = {}  # type: Dict[Identifier, SyncedKey]

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
