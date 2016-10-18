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

from sovrin.test.agent.helper import buildFaberWallet
from sovrin.test.agent.test_walleted_agent import TestWalletedAgent

logger = getlogger()


class FaberAgent(TestWalletedAgent):
    credDefSecretKey = CredDefSecretKey(293672994294601538460023894424280657882248991230397936278278721070227017571960229217003029542172804429372056725385213277754094188540395813914384157706891192254644330822344382798277953427101186508616955910010980515685469918970002852483572038959508885430544201790234678752166995847136179984303153769450295059547,
                                        346129266351333939705152453226207841619953213173429444538411282110012597917194461301159547344552711191280095222396141806532237180979404522416636139654540172375588671099885266296364558380028106566373280517225387715617569246539059672383418036690030219091474419102674344117188434085686103371044898029209202469967)

    def __init__(self,
                 basedirpath: str,
                 client: Client=None,
                 wallet: Wallet=None,
                 port: int=None):
        if not basedirpath:
            config = getConfig()
            basedirpath = basedirpath or os.path.expanduser(config.baseDir)

        portParam, = self.getPassedArgs()

        super().__init__('Faber College', basedirpath, client, wallet,
                         portParam or port)

        self.availableClaims = []

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
        logger.debug("Faber has {} claims: {}".format(len(acl), acl))
        for cd, ik in acl:
            self.availableClaims.append({
                NAME: cd.name,
                VERSION: cd.version,
                "claimDefSeqNo": cd.seqNo
            })

    def addClaimDefsToWallet(self):
        name, version = "Transcript", "1.2"
        attrNames = ["student_name", "ssn", "degree", "year", "status"]
        self.addCredDefAndIskIfNotFoundOnLedger(name, version,
                                                origin=self.wallet.defaultId,
                                                attrNames=attrNames, typ='CL',
                                                credDefSecretKey=
                                                self.credDefSecretKey,
                                                clbk=
                                                self.initAvailableClaimList)

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


def runFaber(name=None, wallet=None, basedirpath=None, port=None,
             startRunning=True, bootstrap=True):

    return runAgent(FaberAgent, name or "Faber College",
                    wallet or buildFaberWallet(), basedirpath,
                    port, startRunning, bootstrap)


if __name__ == "__main__":
    runFaber(port=5555)
