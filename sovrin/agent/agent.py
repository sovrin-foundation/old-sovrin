from plenum.common.motor import Motor
from plenum.common.startable import Status


class Agent(Motor):
    def __init__(self, name="agent1"):
        super().__init__()
        self._name = name

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
