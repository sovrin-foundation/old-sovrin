import os

from plenum.common.log import getlogger

from sovrin.agent.agent import WalletedAgent, runAgent, EVENT_NOTIFY_MSG
from sovrin.agent.exception import NonceNotFound
from sovrin.client.client import Client
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.util import getConfig

from sovrin.test.agent.helper import getAgentCmdLineParams, buildThriftWallet

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

    def postClaimVerif(self, claimName, link, frm):
        if claimName == "Loan-Application-Basic":
            self.notifyToRemoteCaller(EVENT_NOTIFY_MSG,
                                      "    Loan eligibility criteria satisfied,"
                                      " please send another claim "
                                      "'Loan-Application-KYC'\n",
                                      self.wallet.defaultId, frm)

    def addClaimDefsToWallet(self):
        pass

    def getAttributes(self, nonce):
        pass

    def bootstrap(self):
        self.addClaimDefsToWallet()


def runThrift(name=None, wallet=None, basedirpath=None, port=None,
             startRunning=True, bootstrap=True):

    return runAgent(ThriftAgent, name or "Thrift Bank",
                    wallet or buildThriftWallet(), basedirpath,
                    port, startRunning, bootstrap)


if __name__ == "__main__":
    runThrift(port=7777)
