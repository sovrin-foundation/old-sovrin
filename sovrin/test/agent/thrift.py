import os

from plenum.common.log import getlogger

from sovrin.agent.agent import createAgent, runAgent
from sovrin.agent.constants import EVENT_NOTIFY_MSG
from sovrin.agent.exception import NonceNotFound
from sovrin.client.client import Client
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.config_util import getConfig
from sovrin.test.agent.helper import buildThriftWallet
from sovrin.test.agent.test_walleted_agent import TestWalletedAgent
from sovrin.test.helper import TestClient

logger = getlogger()


class ThriftAgent(TestWalletedAgent):
    def __init__(self,
                 basedirpath: str,
                 client: Client = None,
                 wallet: Wallet = None,
                 port: int = None,
                 loop=None):
        if not basedirpath:
            config = getConfig()
            basedirpath = basedirpath or os.path.expanduser(config.baseDir)

        portParam, = self.getPassedArgs()

        super().__init__('Thrift Bank', basedirpath, client, wallet,
                         portParam or port, loop=loop)

        # maps invitation nonces to internal ids
        self._invites = {
            "77fbf9dc8c8e6acde33de98c6d747b28c": 1
        }

    def getInternalIdByInvitedNonce(self, nonce):
        if nonce in self._invites:
            return self._invites[nonce]
        else:
            raise NonceNotFound

    def isClaimAvailable(self, link, claimName):
        return True

    def getAvailableClaimList(self):
        return []

    def _addAtrribute(self, claimDefKey, proverId, link):
        pass

    async def postClaimVerif(self, claimName, link, frm):
        if claimName == "Loan-Application-Basic":
            self.notifyToRemoteCaller(EVENT_NOTIFY_MSG,
                                      "    Loan eligibility criteria satisfied,"
                                      " please send another claim "
                                      "'Loan-Application-KYC'\n",
                                      self.wallet.defaultId, frm)

    async def bootstrap(self):
        pass


def createThrift(name=None, wallet=None, basedirpath=None, port=None):
    return createAgent(ThriftAgent, name or "Thrift Bank",
                       wallet or buildThriftWallet(),
                       basedirpath, port, clientClass=TestClient)


if __name__ == "__main__":
    thrift = createThrift(port=7777)
    runAgent(thrift)
