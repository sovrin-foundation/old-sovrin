import os
import random

from plenum.common.log import getlogger
from plenum.common.txn import NAME, VERSION

from anoncreds.protocol.types import AttribType, AttribDef
from sovrin.agent.agent import WalletedAgent, runAgent
from sovrin.client.client import Client
from sovrin.client.wallet.link import Link
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.util import getConfig
import sovrin.test.random_data as randomData

from anoncreds.test.conftest import staticPrimes
from sovrin.test.agent.helper import getAgentCmdLineParams

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

        portParam, credDefSeqParam, issuerSeqNoParam = getAgentCmdLineParams()

        super().__init__('Acme Corp', basedirpath, client, wallet,
                         portParam or port)

        credDefSeqNo = 12
        issuerSeqNo = 13

        self.availableClaims = []

        self._seqNos = {
            ("Job-Certificate", "0.2"): (credDefSeqParam or credDefSeqNo,
                                         issuerSeqNoParam or issuerSeqNo)
        }

        self._attributes = {
            "57fbf9dc8c8e6acde33de98c6d747b28c": {
                "first_name": "Alice",
                "last_name": "Garcia",
                "ssn": "123-45-6789",
                "employee_status": "Permanent",
                "experience": "3 years",
                "salary_bracket": "between $50,000 to $100,000"
            },
            "3a2eb72eca8b404e8d412c5bf79f2640": {
                "first_name": "Carol",
                "last_name": "Atkinson",
                "ssn": "987-65-4321",
                "employee_status": "Permanent",
                "experience": "2 years",
                "salary_bracket": "between $60,000 to $90,000"
            },
            "8513d1397e87cada4214e2a650f603eb": {
                "first_name": "Frank",
                "last_name": "Jeffrey",
                "ssn": "111-22-3333",
                "employee_status": "Temporary",
                "experience": "4 years",
                "salary_bracket": "between $40,000 to $80,000"
            },
            "810b78be79f29fc81335abaa4ee1c5e8": {
                "first_name": "Craig",
                "last_name": "Richards",
                "ssn": "999-88-7777",
                "employee_status": "On Contract",
                "experience": "3 years",
                "salary_bracket": "between $50,000 to $70,000"
            },
        }

    def addKeyIfNotAdded(self):
        wallet = self.wallet
        if not wallet.identifiers:
            wallet.addSigner(seed=b'Acme0000000000000000000000000000')

    def getAvailableClaimList(self):
        return self.availableClaims

    def postClaimVerification(self, claimName):
        if claimName == "Job-Application":
            self.addAvailableClaimList()

    def addAvailableClaimList(self):
        claimDefSeqNo, _ = self._seqNos.get(("Job-Certificate", "0.2"))
        self.availableClaims.append({
            NAME: "Job-Certificate",
            VERSION: "0.2",
            "claimDefSeqNo": claimDefSeqNo
        })

    def addClaimDefsToWallet(self):
        name, version = "Job-Certificate", "0.2"
        credDefSeqNo, issuerKeySeqNo = self._seqNos[(name, version)]
        staticPrime = staticPrimes().get("prime1")
        attrNames = ["first_name", "last_name", "ssn", "employee_status",
                     "experience", "salary_bracket"]
        super().addClaimDefs(name=name,
                                     version=version,
                                     attrNames=attrNames,
                                     staticPrime=staticPrime,
                                     credDefSeqNo=credDefSeqNo,
                                     issuerKeySeqNo=issuerKeySeqNo)

    def getAttributes(self, nonce):
        attrs = self._attributes.get(nonce)
        if not attrs:
            name = random.choice(randomData.NAMES)
            attrs = {
                "first_name": name.split(' ', 1)[0],
                "last_name": name.split(' ', 1)[1],
                "ssn": random.choice(randomData.SSN),
                "employee_status": random.choice(randomData.EMPLOYEE_STATUS),
                "experience": random.choice(randomData.EXPERIENCE),
                "salary_bracket": random.choice(randomData.SALARY_BRACKET)
            }

        attribTypes = []
        for name in attrs:
            attribTypes.append(AttribType(name, encode=True))
        attribsDef = AttribDef("Job-Certificate", attribTypes)
        attribs = attribsDef.attribs(**attrs)
        return attribs

    def addLinksToWallet(self):
        wallet = self.wallet
        idr = wallet.defaultId
        for nonce, data in self._attributes.items():
            link = Link(data.get("first_name") + " " + data.get("last_name"),
                        idr, nonce=nonce)
            wallet.addLink(link)

    def bootstrap(self):
        self.addKeyIfNotAdded()
        self.addLinksToWallet()
        self.addClaimDefsToWallet()


def runAcme(name=None, wallet=None, basedirpath=None, port=None,
            startRunning=True, bootstrap=True):

    return runAgent(AcmeAgent, name or "Acme Corp", wallet, basedirpath,
             port, startRunning, bootstrap)

if __name__ == "__main__":
    runAcme(port=6666)
