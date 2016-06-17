from typing import Dict, Union, Tuple

from raet.raeting import AutoMode

from plenum.client.signer import Signer
from plenum.common.has_file_storage import HasFileStorage
from plenum.common.stacked import KITStack
from plenum.common.types import HA
from anoncreds.protocol.prover import Prover

from sovrin.client.client import Client
from sovrin.client.anoncreds_role import AnonCredsRole
from sovrin.persistence.entity_file_store import EntityFileStore


class ProverRole(AnonCredsRole):
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
                         main=False,
                         auto=AutoMode.always)
        self.peerStack = KITStack(stackargs, self.handlePeerMessage, {})
        dataDir = "data/provers"
        HasFileStorage.__init__(self, name, baseDir=basedirpath,
                                dataDir=dataDir)

        self.proverStore = EntityFileStore(name=name,
                                           dataDir=self.getDataLocation())

        self.issuers = {}
        self.verifiers = {}
        self.requests = []

    def addProver(self, name: str, prover: Prover):
        pass

    def getProver(self, name: str):
        pass

    def start(self, loop):
        super().start(loop)
        self.peerStack.maintainConnections()

    async def prod(self, limit) -> int:
        super().prod(limit)
        await self.peerStack.serviceLifecycle()

    def handlePeerMessage(self, msg):
        pass

    def addIssuer(self, issuerName: str, issuerHa: HA):
        if issuerName not in self.issuers:
            self.issuers[issuerName] = {
                'ha': issuerHa,
                'credential': None
            }
            self.peerStack.registry[issuerName] = issuerHa
            self.peerStack.maintainConnections()

    def addVerifier(self, verifierName: str, verifierHa: HA):
        if verifierName not in self.verifiers:
            self.verifiers[verifierName] = {
                'ha': verifierHa,
                'credential': None
            }
            self.peerStack.registry[verifierName] = verifierHa
            self.peerStack.maintainConnections()

    def sendCredRequest(self):
        pass
