import os

from anoncreds.protocol.cred_def_secret_key import CredDefSecretKey
from plenum.common.log import getlogger
from plenum.common.txn import NAME, VERSION

from anoncreds.protocol.types import AttribType, AttribDef
from sovrin.agent.agent import runAgent
from sovrin.agent.exception import NonceNotFound
from sovrin.client.client import Client
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.util import getConfig

from sovrin.test.agent.helper import buildAcmeWallet
from sovrin.test.agent.test_walleted_agent import TestWalletedAgent

logger = getlogger()


class AcmeAgent(TestWalletedAgent):
    credDefSecretKey = CredDefSecretKey(
            p=281510790031673293930276619603927743196841646256795847064219403348133278500884496133426719151371079182558480270299769814938220686172645009573713670952475703496783875912436235928500441867163946246219499572100554186255001186037971377948507437993345047481989113938038765221910989549806472045341069625389921020319,
            q=350024478159288302454189301319318317490551219044369889911215183350615705419868722006578530322735670686148639754382100627201250616926263978453441645496880232733783587241897694734699668219445029433427409979471473248066452686224760324273968172651114901114731981044897755380965310877273130485988045688817305189839)

    def __init__(self,
                 basedirpath: str,
                 client: Client=None,
                 wallet: Wallet=None,
                 port: int=None):
        if not basedirpath:
            config = getConfig()
            basedirpath = basedirpath or os.path.expanduser(config.baseDir)

        portParam, = self.getPassedArgs()

        super().__init__('Acme Corp', basedirpath, client, wallet,
                         portParam or port)

        self.availableClaims = []

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
        claimDef = self.wallet.getClaimDef(key=("Job-Certificate", "0.2",
                                                     self.wallet.defaultId))
        return [{
            NAME: "Job-Certificate",
            VERSION: "0.2",
            "claimDefSeqNo": claimDef.seqNo
        }]

    def addClaimDefsToWallet(self):
        name, version = "Job-Certificate", "0.2"
        attrNames = ["first_name", "last_name", "employee_status",
                     "experience", "salary_bracket"]
        self.addCredDefAndIskIfNotFoundOnLedger(name, version,
                                                origin=self.wallet.defaultId,
                                                attrNames=attrNames, typ='CL',
                                                credDefSecretKey=
                                                self.credDefSecretKey)

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
