import os
import random

from plenum.common.log import getlogger

from sovrin.agent.agent import WalletedAgent, runAgent
from sovrin.client.client import Client
from sovrin.client.wallet.link import Link
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.util import getConfig
import sovrin.test.random_data as randomData

from sovrin.test.agent.helper import getAgentCmdLineParams

logger = getlogger()


class ThriftAgent(WalletedAgent):
    def __init__(self,
                 basedirpath: str,
                 client: Client=None,
                 wallet: Wallet=None,
                 port: int=None):
        if not basedirpath:
            config = getConfig()
            basedirpath = basedirpath or os.path.expanduser(config.baseDir)

        portParam, credDefSeqParam, issuerSeqNoParam = getAgentCmdLineParams()

        super().__init__('Thrift Bank', basedirpath, client, wallet,
                         portParam or port)

        self._seqNos = {

        }
        self._attributes = {

        }

    def addKeyIfNotAdded(self):
        wallet = self.wallet
        if not wallet.identifiers:
            wallet.addSigner(seed=b'Thrift00000000000000000000000000')

    def getAvailableClaimList(self):
        return []

    def getClaimList(self, claimNames=None):
        return []

    def addClaimDefsToWallet(self):
        pass

    def getAttributes(self, nonce):
        pass

    def addLinksToWallet(self):
        wallet = self.wallet
        idr = wallet.defaultId
        link = Link(random.choice(randomData.NAMES), idr,
                    nonce="77fbf9dc8c8e6acde33de98c6d747b28c")
        wallet.addLink(link)

    def bootstrap(self):
        self.addKeyIfNotAdded()
        self.addLinksToWallet()
        self.addClaimDefsToWallet()


def runThrift(name=None, wallet=None, basedirpath=None, port=None,
             startRunning=True, bootstrap=True):

    return runAgent(ThriftAgent, name or "Thrift Bank", wallet, basedirpath,
                    port, startRunning, bootstrap)


if __name__ == "__main__":
    runThrift(port=7777)
