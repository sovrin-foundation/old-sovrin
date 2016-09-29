import os
import random
import uuid

from plenum.common.looper import Looper
from plenum.common.txn import NAME, TYPE
from plenum.common.txn import VERSION
from plenum.common.util import getlogger, randomString
from plenum.test.helper import genHa

from anoncreds.protocol.types import AttribType, AttribDef
from sovrin.agent.agent import WalletedAgent, runAgent
from sovrin.client.client import Client
from sovrin.client.wallet.cred_def import CredDef, IssuerPubKey
from sovrin.client.wallet.link import Link
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.txn import ATTR_NAMES
from sovrin.common.util import getConfig
import sovrin.test.random_data as randomData

from anoncreds.protocol.attribute_repo import InMemoryAttrRepo
from anoncreds.protocol.cred_def_secret_key import CredDefSecretKey
from anoncreds.protocol.issuer_secret_key import IssuerSecretKey
from anoncreds.test.conftest import staticPrimes

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
        self._seqNos = {
            ("Transcript", "1.2"): (None, None)
        }
        self._attributes = {
            "b1134a647eb818069c089e7694f63e6d": {
                "student_name": "Alice Garcia",
                "ssn": "123456789",
                "degree": "Bachelor of Science, Marketing",
                "year": "2015",
                "status": "graduated"
            },
            "2a2eb72eca8b404e8d412c5bf79f2640": {
                "student_name": "Carol Atkinson",
                "ssn": "783412695",
                "degree": "Bachelor of Science, Physics",
                "year": "2012",
                "status": "graduated"
            },
            "7513d1397e87cada4214e2a650f603eb": {
                "student_name": "Frank Jeffrey",
                "ssn": "996541211",
                "degree": "Bachelor of Arts, History",
                "year": "2013",
                "status": "dropped"
            },
            "710b78be79f29fc81335abaa4ee1c5e8": {
                "student_name": "Craig Richards",
                "ssn": "151445876",
                "degree": "MBA, Finance",
                "year": "2014",
                "status": "graduated"
            }
        }

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

    def addKeyIfNotAdded(self):
        wallet = self.wallet
        if not wallet.identifiers:
            wallet.addSigner(seed=b'Faber000000000000000000000000000')

    def addClaimDefsToWallet(self):
        name, version = "Transcript", "1.2"
        CredDefSeqNo, IssuerKeySeqNo = self._seqNos[(name, version)]
        csk = CredDefSecretKey(*staticPrimes().get("prime1"))
        sid = self.wallet.addCredDefSk(str(csk))
        # Need to modify the claim definition. We do not support types yet
        claimDef = {
            NAME: name,
            VERSION: version,
            TYPE: "CL",
            ATTR_NAMES: ["student_name", "ssn", "degree", "year", "status"]
        }
        wallet = self.wallet
        credDef = CredDef(seqNo=CredDefSeqNo,
                          attrNames=claimDef[ATTR_NAMES],
                          name=claimDef[NAME],
                          version=claimDef[VERSION],
                          origin=wallet.defaultId,
                          typ=claimDef[TYPE],
                          secretKey=sid)
        wallet._credDefs[(name, version, wallet.defaultId)] = credDef
        isk = IssuerSecretKey(credDef, csk, uid=str(uuid.uuid4()))
        self.wallet.addIssuerSecretKey(isk)
        ipk = IssuerPubKey(N=isk.PK.N, R=isk.PK.R, S=isk.PK.S, Z=isk.PK.Z,
                           claimDefSeqNo=credDef.seqNo,
                           secretKeyUid=isk.uid, origin=wallet.defaultId,
                           seqNo=IssuerKeySeqNo)
        key = (wallet.defaultId, CredDefSeqNo)
        wallet._issuerPks[key] = ipk

    def addLinksToWallet(self):
        wallet = self.wallet
        idr = wallet.defaultId
        for nonce, data in self._attributes.items():
            link = Link(data.get("student_name"), idr, nonce=nonce)
            wallet.addLinkInvitation(link)

    def getAttributes(self, nonce):
        attrs = self._attributes.get(nonce)
        if not attrs:
            attrs = {
                "student_name": random.choice(randomData.NAMES),
                "ssn": random.choice(randomData.SSN),
                "degree": random.choice(randomData.DEGREE),
                "year": random.choice(randomData.YEAR),
                "status": random.choice(randomData.STATUS)
            }

        attribTypes = []
        for name in attrs:
            attribTypes.append(AttribType(name, encode=True))
        attribsDef = AttribDef("Transcript", attribTypes)
        attribs = attribsDef.attribs(**attrs)
        return attribs

    def bootstrap(self):
        self.addKeyIfNotAdded()
        self.addLinksToWallet()
        self.addClaimDefsToWallet()


def runFaber(name=None, wallet=None, basedirpath=None, port=None,
             startRunning=True, bootstrap=True):

    return runAgent(FaberAgent, name or "Faber College", wallet, basedirpath,
                    port, startRunning, bootstrap)


if __name__ == "__main__":
    runFaber(port=5555)
