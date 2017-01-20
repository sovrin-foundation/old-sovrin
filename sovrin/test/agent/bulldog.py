import os

from plenum.common.txn import NAME, VERSION

from anoncreds.protocol.types import AttribType, AttribDef, ID, ClaimDefinitionKey
from sovrin.agent.agent import createAgent, runAgent
from sovrin.agent.exception import NonceNotFound
from sovrin.client.client import Client
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.config_util import getConfig
from sovrin.test.agent.helper import buildBulldogWallet
from sovrin.test.agent.test_walleted_agent import TestWalletedAgent
from sovrin.test.conftest import primes
from sovrin.test.helper import TestClient
from sovrin.test.agent.bulldog_helper import bulldogLogger


class BulldogAgent(TestWalletedAgent):
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

        super().__init__('Bulldog', basedirpath, client, wallet,
                         portParam or port, loop=loop,
                         agentLogger=bulldogLogger)

        self.availableClaims = []

        # maps invitation nonces to internal ids
        self._invites = {
            '2e9882ea71976ddf9': 1,
            "2d03828a7383ea3ad": 2
        }

        self._attrDef = AttribDef('bulldog',
                                  [AttribType('title', encode=True),
                                   AttribType('first_name', encode=True),
                                   AttribType('last_name', encode=True),
                                   AttribType('address_1', encode=True),
                                   AttribType('address_2', encode=True),
                                   AttribType('address_3', encode=True),
                                   AttribType('postcode_zip', encode=True),
                                   AttribType('date_of_birth', encode=True),
                                   AttribType('account_type', encode=True),
                                   AttribType('year_opened', encode=True),
                                   AttribType('account_status', encode=True)
                                   ])

        # maps internal ids to attributes
        self._attrs = {
            1: self._attrDef.attribs(
                title='Mrs.',
                first_name='Alicia',
                last_name='Garcia',
                address_1='H-301',
                address_2='Street 1',
                address_3='UK',
                postcode_zip='G61 3NR',
                date_of_birth='December 28, 1990',
                account_type='savings',
                year_opened='2000',
                account_status='active'),
            2: self._attrDef.attribs(
                title='Mrs.',
                first_name='Jay',
                last_name='Raj',
                address_1='222',
                address_2='Baker Street',
                address_3='UK',
                postcode_zip='G61 3NR',
                date_of_birth='January 15, 1980',
                account_type='savings',
                year_opened='1999',
                account_status='active')
        }

        claimVersionFileName = 'bulldog-claim-def-version.txt'
        claimVersionNumber = 0.8
        claimVersionFilePath = '{}/{}'.format(basedirpath, claimVersionFileName)
        # get version number from file
        if os.path.isfile(claimVersionFilePath):
            try:
                with open(claimVersionFilePath, mode='r+') as file:
                    claimVersionNumber = float(file.read()) + 0.1
                    file.seek(0)
                    # increment version and update file
                    file.write(str(claimVersionNumber))
                    file.truncate()
            except OSError as e:
                bulldogLogger.warn('Error occurred while reading version file:'
                                   'error:{}'.format(e))
                raise e
            except ValueError as e:
                bulldogLogger.warn('Invalid version number')
                raise e
        else:
            try:
                with open(claimVersionFilePath, mode='w') as file:
                    file.write(str(claimVersionNumber))
            except OSError as e:
                bulldogLogger.warn('Error creating version file {}'.format(e))
                raise e

        self._claimDefKey = ClaimDefinitionKey('Banking-Relationship',
                                               str(claimVersionNumber),
                                               self.wallet.defaultId)

    def getInternalIdByInvitedNonce(self, nonce):
        if nonce in self._invites:
            return self._invites[nonce]
        else:
            raise NonceNotFound

    def isClaimAvailable(self, link, claimName):
        return claimName == 'Banking-Relationship'

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


def createBulldog(name=None, wallet=None, basedirpath=None, port=None):
    return createAgent(BulldogAgent, name or "Bulldog",
                       wallet or buildBulldogWallet(),
                       basedirpath, port, clientClass=TestClient)


if __name__ == "__main__":
    bulldog = createBulldog(port=8787)
    runAgent(bulldog)
