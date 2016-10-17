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
from sovrin.test.agent.helper import getAgentCmdLineParams, buildFaberWallet

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

        portParam, credDefSeqParam, issuerSeqNoParam = self.getPassedArgs()

        super().__init__('Faber College', basedirpath, client, wallet,
                         portParam or port)

        credDefSeqNo = 10
        issuerSeqNo = 11

        self.availableClaims = []

        self._seqNos = {
            ("Transcript", "1.2"): (credDefSeqParam or credDefSeqNo,
                                    issuerSeqNoParam or issuerSeqNo)
        }

        # maps invitation nonces to internal ids
        self._invites = {
            "b1134a647eb818069c089e7694f63e6d": 1,
            "2a2eb72eca8b404e8d412c5bf79f2640": 2,
            "7513d1397e87cada4214e2a650f603eb": 3,
            "710b78be79f29fc81335abaa4ee1c5e8": 4
        }

        # maps internal ids to attributes
        self._attributes = {
            1: {
                "student_name": "Alice Garcia",
                "ssn": "123-45-6789",
                "degree": "Bachelor of Science, Marketing",
                "year": "2015",
                "status": "graduated"
            },
            2: {
                "student_name": "Carol Atkinson",
                "ssn": "783-41-2695",
                "degree": "Bachelor of Science, Physics",
                "year": "2012",
                "status": "graduated"
            },
            3: {
                "student_name": "Frank Jeffrey",
                "ssn": "996-54-1211",
                "degree": "Bachelor of Arts, History",
                "year": "2013",
                "status": "dropped"
            },
            4: {
                "student_name": "Craig Richards",
                "ssn": "151-44-5876",
                "degree": "MBA, Finance",
                "year": "2014",
                "status": "graduated"
            }
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
        if claimName == "Transcript":
            return True
        else:
            return False

    def getAvailableClaimList(self):
        return self.availableClaims

    def postClaimVerif(self, claimName, link, frm):
        pass

    def initAvailableClaimList(self):
        acl = self.wallet.getAvailableClaimList()
        for cd, ik in acl:
            self.availableClaims.append({
                NAME: cd.name,
                VERSION: cd.version,
                "claimDefSeqNo": cd.seqNo
            })

    def addClaimDefsToWallet(self):
        name, version = "Transcript", "1.2"
        credDefSeqNo, issuerKeySeqNo = self._seqNos[(name, version)]
        staticPrime = staticPrimes().get("prime1")
        attrNames = ["student_name", "ssn", "degree", "year", "status"]
        super().addClaimDefs(name=name,
                             version=version,
                             attrNames=attrNames,
                             staticPrime=staticPrime,
                             credDefSeqNo=credDefSeqNo,
                             issuerKeySeqNo=issuerKeySeqNo)

    def getAttributes(self, internalId):
        attrs = self._attributes.get(internalId)

        if not attrs:
            raise RuntimeError('attributes for internal ID {} not found'.
                               format(internalId))

        attribTypes = []
        for name in attrs:
            attribTypes.append(AttribType(name, encode=True))
        attribsDef = AttribDef("Transcript", attribTypes)
        attribs = attribsDef.attribs(**attrs)
        return attribs

    def bootstrap(self):
        self.addClaimDefsToWallet()
        self.initAvailableClaimList()


def runFaber(name=None, wallet=None, basedirpath=None, port=None,
             startRunning=True, bootstrap=True):

    return runAgent(FaberAgent, name or "Faber College",
                    wallet or buildFaberWallet(), basedirpath,
                    port, startRunning, bootstrap)


if __name__ == "__main__":
    runFaber(port=5555)
