import json
from typing import Dict, Union, Tuple

from raet.raeting import AutoMode

from plenum.client.signer import Signer
from plenum.common.has_file_storage import HasFileStorage
from plenum.common.stacked import SimpleStack
from plenum.common.txn import ORIGIN, TARGET_NYM, TXN_TYPE, DATA
from plenum.common.types import HA
from anoncreds.protocol.issuer import Issuer

from sovrin.client.anoncreds_role import AnonCredsRole
from sovrin.client.client import Client
from sovrin.common.txn import ADD_PKI
from sovrin.persistence.entity_file_store import EntityFileStore


class IssuerRole(AnonCredsRole):
    def __init__(self,
                 client: Client,
                 name: str,
                 nodeReg: Dict[str, HA]=None,
                 sovrinHa: Union[HA, Tuple[str, int]]=None,
                 p2pHa: Union[HA, Tuple[str, int]]=None,
                 lastReqId: int = 0,
                 signer: Signer=None,
                 signers: Dict[str, Signer]=None,
                 basedirpath: str=None):
        super().__init__(name, nodeReg, sovrinHa=sovrinHa,
                         p2pHa=p2pHa,
                         lastReqId=lastReqId, signer=signer,
                         signers=signers,
                         basedirpath=basedirpath)
        stackargs = dict(name=name,
                         ha=p2pHa,
                         main=True,
                         auto=AutoMode.always)
        self.peerStack = SimpleStack(stackargs, self.handlePeerMessage)
        dataDir = "data/issuers"
        HasFileStorage.__init__(self, name, baseDir=basedirpath,
                                dataDir=dataDir)
        self.issuerStore = EntityFileStore(name=name,
                                           dataDir=self.getDataLocation())
        self.provers = {}
        self.issuers = {}

    def hasIssuer(self, attrNames: Tuple[str]) -> bool:
        return attrNames in self.issuers

    def createIssuer(self, attrNames: Tuple[str]):
        self.issuers[attrNames] = Issuer(attrNames)

    def persistIssuer(self, name: str, issuer: Issuer):
        pk = issuer.PK
        R = [v for k, v in sorted(pk['R'].items(), key=lambda x: int(x[0]))]
        issuerData = ",".join([str(n) for n in (
            issuer.p_prime,
            issuer.q_prime,
            issuer.p,
            issuer.q,
            pk['N'],
            pk['S'],
            pk['Z'],
            '|'.join(R),
        )])
        self.issuerStore.add(name, issuerData)

    def retrieveIssuer(self, name: str):
        issuerData = self.issuerStore.get(name)
        p_prime, q_prime, p, q, N, S, Z, R = issuerData.split(",")
        R = {str(i+1): r for i, r, in R.split("|")}
        issuer = Issuer(len(R))
        issuer.p = p
        issuer.q = q
        issuer.p_prime = p_prime
        issuer.q_prime = q_prime
        issuer._pk = {'N': N, 'S': S, 'Z': Z, 'R': R}
        issuer.sk = {'p': p, 'q': q}
        return issuer

    def addProver(self, proverNym, attributes):
        self.provers[proverNym] = {
            "attributes": attributes,
            "issuer": Issuer(len(attributes))
        }

    def addPkiToLedger(self, attrNames):
        attrNames = tuple(sorted(attrNames))
        if not self.hasIssuer(attrNames):
            self.createIssuer(attrNames)
        issuer = self.issuers[attrNames]

        issuerNym = self.sovrinClient.defaultIdentifier

        pk = {
            "N": int(issuer.PK["N"]),
            "R": {k: int(v) for k, v in issuer.PK["R"].items()},
            "S": int(issuer.PK["S"]),
            "Z": int(issuer.PK["Z"]),
        }
        op = {
            ORIGIN: issuerNym,
            TARGET_NYM: issuerNym,
            TXN_TYPE: ADD_PKI,
            DATA: json.dumps({
                "public_key": pk,
                "atrribute_names": attrNames
            })
        }
        return self.sovrinClient.submit(op)

    def handlePeerMessage(self, wrappedMsg):
        msg, frm = wrappedMsg
        print(wrappedMsg)
