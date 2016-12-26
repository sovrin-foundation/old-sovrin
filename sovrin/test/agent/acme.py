import os

from plenum.common.log import getlogger
from plenum.common.txn import NAME, VERSION

from anoncreds.protocol.types import AttribType, AttribDef, ClaimDefinitionKey, \
    ID
from sovrin.agent.agent import createAgent, runAgent
from sovrin.agent.exception import NonceNotFound
from sovrin.client.client import Client
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.config_util import getConfig
from sovrin.test.agent.helper import buildAcmeWallet
from sovrin.test.agent.test_walleted_agent import TestWalletedAgent
from sovrin.test.conftest import primes
from sovrin.test.helper import TestClient

logger = getlogger()


class AcmeAgent(TestWalletedAgent):
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

        super().__init__('Acme Corp', basedirpath, client, wallet,
                         portParam or port, loop=loop)

        self.availableClaims = []

        # maps invitation nonces to internal ids
        self._invites = {
            "57fbf9dc8c8e6acde33de98c6d747b28c": 1,
            "3a2eb72eca8b404e8d412c5bf79f2640": 2,
            "8513d1397e87cada4214e2a650f603eb": 3,
            "810b78be79f29fc81335abaa4ee1c5e8": 4
        }

        self._attrDefJobCert = AttribDef('Acme Job Certificat',
                                         [AttribType('first_name', encode=True),
                                          AttribType('last_name', encode=True),
                                          AttribType('employee_status',
                                                     encode=True),
                                          AttribType('experience', encode=True),
                                          AttribType('salary_bracket',
                                                     encode=True)])

        self._attrDefJobApp = AttribDef('Acme Job Application',
                                        [AttribType('first_name', encode=True),
                                         AttribType('last_name', encode=True),
                                         AttribType('phone_number',
                                                    encode=True),
                                         AttribType('degree', encode=True),
                                         AttribType('status', encode=True),
                                         AttribType('ssn', encode=True)])

        # maps internal ids to attributes
        self._attrsJobCert = {
            1: self._attrDefJobCert.attribs(
                first_name="Alice",
                last_name="Garcia",
                employee_status="Permanent",
                experience="3 years",
                salary_bracket="between $50,000 to $100,000"),
            2: self._attrDefJobCert.attribs(
                first_name="Carol",
                last_name="Atkinson",
                employee_status="Permanent",
                experience="2 years",
                salary_bracket="between $60,000 to $90,000"),
            3: self._attrDefJobCert.attribs(
                first_name="Frank",
                last_name="Jeffrey",
                employee_status="Temporary",
                experience="4 years",
                salary_bracket="between $40,000 to $80,000"),
            4: self._attrDefJobCert.attribs(
                first_name="Craig",
                last_name="Richards",
                employee_status="On Contract",
                experience="3 years",
                salary_bracket="between $50,000 to $70,000")
        }

        self._claimDefJobCertKey = ClaimDefinitionKey("Job-Certificate", "0.2",
                                                      self.wallet.defaultId)
        self._claimDefJobAppKey = ClaimDefinitionKey("Job-Application", "0.2",
                                                     self.wallet.defaultId)

    def _addAtrribute(self, claimDefKey, proverId, link):
        attr = self._attrsJobCert[self.getInternalIdByInvitedNonce(proverId)]
        self.issuer._attrRepo.addAttributes(claimDefKey=claimDefKey,
                                            userId=proverId,
                                            attributes=attr)

    def getInternalIdByInvitedNonce(self, nonce):
        if nonce in self._invites:
            return self._invites[nonce]
        else:
            raise NonceNotFound

    def isClaimAvailable(self, link, claimName):
        return claimName == "Job-Certificate" and \
               "Job-Application" in link.verifiedClaimProofs

    def getAvailableClaimList(self):
        return self.availableClaims

    async def postClaimVerif(self, claimName, link, frm):
        nac = await self.newAvailableClaimsPostClaimVerif(claimName)
        self.sendNewAvailableClaimsData(nac, frm, link)

    async def newAvailableClaimsPostClaimVerif(self, claimName):
        if claimName == "Job-Application":
            return await self.getJobCertAvailableClaimList()

    async def getJobCertAvailableClaimList(self):
        claimDef = await self.issuer.wallet.getClaimDef(
            ID(self._claimDefJobCertKey))
        return [{
            NAME: claimDef.name,
            VERSION: claimDef.version,
            "claimDefSeqNo": claimDef.seqId
        }]

    async def addClaimDefsToWallet(self):
        claimDefJobCert = await self.issuer.genClaimDef(
            self._claimDefJobCertKey.name,
            self._claimDefJobCertKey.version,
            self._attrDefJobCert.attribNames(),
            'CL')
        claimDefJobCertId = ID(claimDefKey=claimDefJobCert.getKey(),
                               claimDefId=claimDefJobCert.seqId)
        p_prime, q_prime = primes["prime1"]
        await self.issuer.genKeys(claimDefJobCertId, p_prime=p_prime,
                                  q_prime=q_prime)
        await self.issuer.issueAccumulator(claimDefId=claimDefJobCertId, iA='110', L=5)

    async def bootstrap(self):
        await self.addClaimDefsToWallet()


def createAcme(name=None, wallet=None, basedirpath=None, port=None):
    return createAgent(AcmeAgent, name or "Acme Corp",
                       wallet or buildAcmeWallet(),
                       basedirpath, port, clientClass=TestClient)


if __name__ == "__main__":
    acme = createAcme(port=6666)
    runAgent(acme)
