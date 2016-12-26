import os

from plenum.common.log import getlogger
from plenum.common.txn import NAME, VERSION

from anoncreds.protocol.types import AttribType, AttribDef, ID, ClaimDefinitionKey
from sovrin.agent.agent import createAgent, runAgent
from sovrin.agent.exception import NonceNotFound
from sovrin.client.client import Client
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.config_util import getConfig
from sovrin.test.agent.helper import buildFaberWallet
from sovrin.test.agent.test_walleted_agent import TestWalletedAgent
from sovrin.test.conftest import primes
from sovrin.test.helper import TestClient

logger = getlogger()


class FaberAgent(TestWalletedAgent):
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

        super().__init__('Faber College', basedirpath, client, wallet,
                         portParam or port, loop=loop)

        self.availableClaims = []

        # maps invitation nonces to internal ids
        self._invites = {
            "b1134a647eb818069c089e7694f63e6d": 1,
            "2a2eb72eca8b404e8d412c5bf79f2640": 2,
            "7513d1397e87cada4214e2a650f603eb": 3,
            "710b78be79f29fc81335abaa4ee1c5e8": 4
        }

        self._attrDef = AttribDef('faber',
                                  [AttribType('student_name', encode=True),
                                   AttribType('ssn', encode=True),
                                   AttribType('degree', encode=True),
                                   AttribType('year', encode=True),
                                   AttribType('status', encode=True)])

        # maps internal ids to attributes
        self._attrs = {
            1: self._attrDef.attribs(
                student_name="Alice Garcia",
                ssn="123-45-6789",
                degree="Bachelor of Science, Marketing",
                year="2015",
                status="graduated"),
            2: self._attrDef.attribs(
                student_name="Carol Atkinson",
                ssn="783-41-2695",
                degree="Bachelor of Science, Physics",
                year="2012",
                status="graduated"),
            3: self._attrDef.attribs(
                student_name="Frank Jeffrey",
                ssn="996-54-1211",
                degree="Bachelor of Arts, History",
                year="2013",
                status="dropped"),
            4: self._attrDef.attribs(
                student_name="Craig Richards",
                ssn="151-44-5876",
                degree="MBA, Finance",
                year="2015",
                status="graduated")
        }

        self._claimDefKey = ClaimDefinitionKey("Transcript", "1.2", self.wallet.defaultId)

    def getInternalIdByInvitedNonce(self, nonce):
        if nonce in self._invites:
            return self._invites[nonce]
        else:
            raise NonceNotFound

    def isClaimAvailable(self, link, claimName):
        return claimName == "Transcript"

    def getAvailableClaimList(self):
        return self.availableClaims

    async def postClaimVerif(self, claimName, link, frm):
        pass

    async def initAvailableClaimList(self):
        claimDef = await self.issuer.wallet.getClaimDef(ID(self._claimDefKey))
        self.availableClaims.append({
            NAME: claimDef.name,
            VERSION: claimDef.version,
            "claimDefSeqNo": claimDef.seqId
        })

    def _addAtrribute(self, claimDefKey, proverId, link):
        attr = self._attrs[self.getInternalIdByInvitedNonce(proverId)]
        self.issuer._attrRepo.addAttributes(claimDefKey=claimDefKey,
                                            userId=proverId,
                                            attributes=attr)

    async def addClaimDefsToWallet(self):
        claimDef = await self.issuer.genClaimDef(self._claimDefKey.name,
                                                 self._claimDefKey.version,
                                                 self._attrDef.attribNames(),
                                                 'CL')
        claimDefId = ID(claimDefKey=claimDef.getKey(), claimDefId=claimDef.seqId)
        p_prime, q_prime = primes["prime2"]
        await self.issuer.genKeys(claimDefId, p_prime=p_prime, q_prime=q_prime)
        await self.issuer.issueAccumulator(claimDefId=claimDefId, iA='110', L=5)
        await self.initAvailableClaimList()

    async def bootstrap(self):
        await self.addClaimDefsToWallet()


def createFaber(name=None, wallet=None, basedirpath=None, port=None):
    return createAgent(FaberAgent, name or "Faber College",
                       wallet or buildFaberWallet(),
                       basedirpath, port, clientClass=TestClient)


if __name__ == "__main__":
    faber = createFaber(port=5555)
    runAgent(faber)
