from plenum.common.log import getlogger
from plenum.common.types import f
from plenum.test.testable import Spyable

from sovrin.agent.agent import WalletedAgent
from sovrin.common.exceptions import LinkNotFound
from sovrin.common.txn import NONCE
from sovrin.test.agent.helper import getAgentCmdLineParams

logger = getlogger()


@Spyable(
    methods=[WalletedAgent._handlePing, WalletedAgent._handlePong])
class TestWalletedAgent(WalletedAgent):
    def getLinkForMsg(self, msg):
        nonce = msg.get(NONCE)
        identifier = msg.get(f.IDENTIFIER.nm)
        link = None
        for _, li in self.wallet._links.items():
            if li.invitationNonce == nonce and li.remoteIdentifier == identifier:
                link = li
                break
        if link:
            return link
        else:
            raise LinkNotFound

    @staticmethod
    def getPassedArgs():
        return getAgentCmdLineParams()
