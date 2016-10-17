import os

from plenum.common.log import getlogger
from plenum.common.txn import NAME, VERSION

from anoncreds.protocol.types import AttribType, AttribDef
from sovrin.agent.agent import runAgent
from sovrin.agent.agent import WalletedAgent
from sovrin.agent.exception import NonceNotFound
from sovrin.client.client import Client
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.util import getConfig

from anoncreds.test.conftest import staticPrimes
from sovrin.test.agent.helper import getAgentCmdLineParams, buildAcmeWallet

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

        portParam, credDefSeqParam, issuerSeqNoParam = self.getPassedArgs()

        super().__init__('Acme Corp', basedirpath, client, wallet,
                         portParam or port)

        credDefSeqNo = 12
        issuerSeqNo = 13

        self.availableClaims = []

        self._seqNos = {
            ("Job-Certificate", "0.2"): (credDefSeqParam or credDefSeqNo,
                                         issuerSeqNoParam or issuerSeqNo)
        }

        # maps invitation nonces to internal ids
        self._invites = {
            "57fbf9dc8c8e6acde33de98c6d747b28c": 1,
            "3a2eb72eca8b404e8d412c5bf79f2640": 2,
            "8513d1397e87cada4214e2a650f603eb": 3,
            "810b78be79f29fc81335abaa4ee1c5e8": 4
        }

        self._attributes = {
            1: {
                "first_name": "Alice",
                "last_name": "Garcia",
                "employee_status": "Permanent",
                "experience": "3 years",
                "salary_bracket": "between $50,000 to $100,000"
            },
            2: {
                "first_name": "Carol",
                "last_name": "Atkinson",
                "employee_status": "Permanent",
                "experience": "2 years",
                "salary_bracket": "between $60,000 to $90,000"
            },
            3: {
                "first_name": "Frank",
                "last_name": "Jeffrey",
                "employee_status": "Temporary",
                "experience": "4 years",
                "salary_bracket": "between $40,000 to $80,000"
            },
            4: {
                "first_name": "Craig",
                "last_name": "Richards",
                "employee_status": "On Contract",
                "experience": "3 years",
                "salary_bracket": "between $50,000 to $70,000"
            },
        }

    @staticmethod
    def getPassedArgs():
        return getAgentCmdLineParams()

    def getInternalIdByInvitedNonce(self, nonce):
        if nonce in self._invites:
            return self._invites[nonce]
        else:
            raise NonceNotFound

    def isClaimAvailable(self, link, claimName):
        if claimName == "Job-Certificate" and \
                        "Job-Application" in link.verifiedClaimProofs:
            return True
        else:
            return False

    def getAvailableClaimList(self):
        return self.availableClaims

    def postClaimVerif(self, claimName, link, frm):
        nac = self.newAvailableClaimsPostClaimVerif(claimName)
        self.sendNewAvailableClaimsData(nac, frm, link)

    def newAvailableClaimsPostClaimVerif(self, claimName):
        if claimName == "Job-Application":
            return self.getJobCertAvailableClaimList()

    def getJobCertAvailableClaimList(self):
        claimDefSeqNo, _ = self._seqNos.get(("Job-Certificate", "0.2"))
        return [{
            NAME: "Job-Certificate",
            VERSION: "0.2",
            "claimDefSeqNo": claimDefSeqNo
        }]

    def addClaimDefsToWallet(self):
        name, version = "Job-Certificate", "0.2"
        credDefSeqNo, issuerKeySeqNo = self._seqNos[(name, version)]
        staticPrime = staticPrimes().get("prime1")
        attrNames = ["first_name", "last_name", "employee_status",
                     "experience", "salary_bracket"]
        super().addClaimDefs(name=name,
                                     version=version,
                                     attrNames=attrNames,
                                     staticPrime=staticPrime,
                                     credDefSeqNo=credDefSeqNo,
                                     issuerKeySeqNo=issuerKeySeqNo)

    def getAttributes(self, internalId):
        attrs = self._attributes.get(internalId)
        if not attrs:
            if not attrs:
                raise RuntimeError('attributes for internal ID {} not found'.
                                   format(internalId))

        attribTypes = []
        for name in attrs:
            attribTypes.append(AttribType(name, encode=True))
        attribsDef = AttribDef("Job-Certificate", attribTypes)
        attribs = attribsDef.attribs(**attrs)
        return attribs

    def bootstrap(self):
        self.addClaimDefsToWallet()


def runAcme(name=None, wallet=None, basedirpath=None, port=None,
            startRunning=True, bootstrap=True):

    return runAgent(AcmeAgent, name or "Acme Corp",
                    wallet or buildAcmeWallet(), basedirpath,
             port, startRunning, bootstrap)

if __name__ == "__main__":
    runAcme(port=6666)
