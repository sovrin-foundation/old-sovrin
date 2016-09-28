import os
from typing import Dict

from plenum.common.looper import Looper
from plenum.common.txn import NAME
from plenum.common.util import getlogger, randomString
from plenum.test.helper import genHa
from sovrin.agent.agent import WalletedAgent, runAgent
from sovrin.client.client import Client
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.util import getConfig

logger = getlogger()


class FaberAgent(WalletedAgent):
    def __init__(self,
                 basedirpath: str,
                 client: Client=None,
                 wallet: Wallet=None,
                 port: int=None):
        if not basedirpath:
            config = getConfig()
            basedirpath = basedirpath or os.path.expanduser(config.baseDir)

        super().__init__('Faber College', basedirpath, client, wallet, port)

    def getClaimList(self, claimNames=None):
        allClaims = [{
            "name": "Transcript",
            "version": "1.2",
            "claimDefSeqNo": "<claimDefSeqNo>",
            "values": {
                "student_name": "Alice Garcia",
                "ssn": "123456789",
                "degree": "Bachelor of Science, Marketing",
                "year": "2015",
                "status": "graduated"
            }
        }]
        return [c for c in allClaims if not claimNames or c[NAME] in claimNames]

    def getAvailableClaimList(self):
        return [{
            "name": "Transcript",
            "version": "1.2",
            "claimDefSeqNo": "<claimDefSeqNo>",
            "definition": {
                "attributes": {
                    "student_name": "string",
                    "ssn": "string",
                    "degree": "string",
                    "year": "string",
                    "status": "string"
                }
            }
        }]


def runFaber(name=None, wallet=None, basedirpath=None, port=None,
             startRunning=True):
    return runAgent(FaberAgent, name or "Faber College", wallet, basedirpath,
             port, startRunning)


if __name__ == "__main__":
    runFaber()
