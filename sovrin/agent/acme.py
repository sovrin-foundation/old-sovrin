import os

from plenum.common.looper import Looper
from plenum.common.txn import NAME
from plenum.common.util import getlogger, randomString
from plenum.test.helper import genHa
from sovrin.agent.agent import WalletedAgent, runAgent
from sovrin.client.client import Client
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.util import getConfig

logger = getlogger()


class AcmeAgent(WalletedAgent):
    def __init__(self,
                 basedirpath: str,
                 client: Client=None,
                 wallet: Wallet=None,
                 port: int=None):
        if not basedirpath:
            config = getConfig()
            basedirpath = basedirpath or os.path.expanduser(config.baseDir)

        super().__init__('Acme Corp', basedirpath, client, wallet, port)

    def getClaimList(self, claimNames=None):
        allClaims = [{
            "name": "Job-Certificate",
            "version": "0.1",
            "claimDefSeqNo": "<claimDefSeqNo>",
            "values": {
                "employee_name": "Alice Gracia",
                "employee_status": "Permanent",
                "experience": "3 years",
                "salary_bracket": "between $50,000 to $100,000"
            }
        }]
        return [c for c in allClaims if not claimNames or c[NAME] in claimNames]

    def getAvailableClaimList(self):
        return [{
            "name": "Job-Certificate",
            "version": "0.1",
            "claimDefSeqNo": "<claimDefSeqNo>",
            "definition": {
                "attributes": {
                    "employee_name": "string",
                    "employee_status": "string",
                    "experience": "string",
                    "salary_bracket": "string"
                }
            }
        }]


def runAcme(name=None, wallet=None, basedirpath=None, port=None,
            startRunning=True):
    return runAgent(AcmeAgent, name or "Acme Corp", wallet, basedirpath,
             port, startRunning)

if __name__ == "__main__":
    runAcme()
