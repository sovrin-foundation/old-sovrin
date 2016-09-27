import os

from plenum.common.looper import Looper
from plenum.common.util import getlogger, randomString
from plenum.test.helper import genHa
from sovrin.agent.agent import WalletedAgent
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

    def getClaimList(self):
        return [{
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


def runAcme(name=None, wallet=None, basedirpath=None, startRunning=True):
    _, port = genHa()
    _, clientPort = genHa()
    client = Client(randomString(6),
                    ha=("0.0.0.0", clientPort),
                    basedirpath=basedirpath)

    acme = AcmeAgent(basedirpath=basedirpath,
                       client=client,
                       wallet=wallet,
                       port=port)
    if startRunning:
        with Looper(debug=True) as looper:
            looper.add(acme)
            logger.debug("Running Acme Corp now...")
            looper.run()
    else:
        return acme


if __name__ == "__main__":
    runAcme()
