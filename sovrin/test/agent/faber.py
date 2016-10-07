import os
import random

import sys
from plenum.common.log import getlogger
from plenum.common.txn import NAME
from plenum.common.txn import VERSION

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


class FaberAgent(WalletedAgent):
    def __init__(self,
                 basedirpath: str,
                 client: Client=None,
                 wallet: Wallet=None,
                 port: int=None):
        if not basedirpath:
            config = getConfig()
            basedirpath = basedirpath or os.path.expanduser(config.baseDir)

        portParam, credDefSeqParam, issuerSeqNoParam = getAgentCmdLineParams()

        super().__init__('Faber College', basedirpath, client, wallet,
                         portParam or port)

        credDefSeqNo = 10
        issuerSeqNo = 11

        self._seqNos = {
            ("Transcript", "1.2"): (credDefSeqParam or credDefSeqNo,
                                    issuerSeqNoParam or issuerSeqNo)
        }
        self._attributes = {
            "b1134a647eb818069c089e7694f63e6d": {
                "student_name": "Alice Garcia",
                "ssn": "123-45-6789",
                "degree": "Bachelor of Science, Marketing",
                "year": "2015",
                "status": "graduated"
            },
            "2a2eb72eca8b404e8d412c5bf79f2640": {
                "student_name": "Carol Atkinson",
                "ssn": "783-41-2695",
                "degree": "Bachelor of Science, Physics",
                "year": "2012",
                "status": "graduated"
            },
            "7513d1397e87cada4214e2a650f603eb": {
                "student_name": "Frank Jeffrey",
                "ssn": "996-54-1211",
                "degree": "Bachelor of Arts, History",
                "year": "2013",
                "status": "dropped"
            },
            "710b78be79f29fc81335abaa4ee1c5e8": {
                "student_name": "Craig Richards",
                "ssn": "151-44-5876",
                "degree": "MBA, Finance",
                "year": "2014",
                "status": "graduated"
            }
        }

    def addKeyIfNotAdded(self):
        wallet = self.wallet
        if not wallet.identifiers:
            wallet.addSigner(seed=b'Faber000000000000000000000000000')

    def getAvailableClaimList(self):
        acl = self.wallet.getAvailableClaimList()
        resp = []
        for cd, ik in acl:
            resp.append({
                NAME: cd.name,
                VERSION: cd.version,
                "claimDefSeqNo": cd.seqNo
            })
        return resp

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


    def addLinksToWallet(self):
        wallet = self.wallet
        idr = wallet.defaultId
        for nonce, data in self._attributes.items():
            link = Link(data.get("student_name"), idr, nonce=nonce)
            wallet.addLink(link)

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
