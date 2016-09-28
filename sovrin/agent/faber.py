import os
from typing import Dict

from plenum.common.looper import Looper
from plenum.common.txn import NAME
from plenum.common.txn import VERSION
from plenum.common.util import getlogger, randomString
from plenum.test.helper import genHa
from sovrin.agent.agent import WalletedAgent
from sovrin.client.client import Client
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.util import getConfig

from anoncreds.protocol.attribute_repo import InMemoryAttrRepo

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
        self.attributeRepo = InMemoryAttrRepo()

    def getClaimList(self):
        return [{
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

    def getAvailableClaimList(self):
        acl = self.wallet.getAvailableClaimList()
        resp = []
        for cd, ik in acl:
            attrs = {}
            for a in cd.attrNames:
                attrs[a] = "string"
            resp.append({
                NAME: cd.name,
                VERSION: cd.version,
                "claimDefSeqNo": cd.seqNo,
                "issuerKeySeqNo": ik.seqNo,
                "definition": {
                    "attributes": attrs
                }
            })
        return resp


def runFaber(name=None, wallet=None, basedirpath=None, port=None,
             startRunning=True):
    if not port:
        _, port = genHa()
    _, clientPort = genHa()
    client = Client(randomString(6),
                    ha=("0.0.0.0", clientPort),
                    basedirpath=basedirpath)

    faber = FaberAgent(basedirpath=basedirpath,
                       client=client,
                       wallet=wallet,
                       port=port)
    if startRunning:
        with Looper(debug=True) as looper:
            looper.add(faber)
            logger.debug("Running Faber now...")
            looper.run()
    else:
        return faber


if __name__ == "__main__":
    runFaber()
