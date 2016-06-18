from typing import Dict, Union, Tuple

from raet.raeting import AutoMode

from plenum.client.signer import Signer
from plenum.common.has_file_storage import HasFileStorage
from plenum.common.stacked import SimpleStack
from plenum.common.types import HA
from sovrin.client.anoncreds_role import AnonCredsRole
from sovrin.client.client import Client
from anoncreds.protocol.verifier import Verifier

from sovrin.persistence.entity_file_store import EntityFileStore


class VerifierRole(AnonCredsRole):
    def __init__(self,
                 client: Client,
                 name: str,
                 nodeReg: Dict[str, HA]=None,
                 sovrinHa: Union[HA, Tuple[str, int]]=None,
                 p2pHa: Union[HA, Tuple[str, int]]=None,
                 lastReqId: int=0,
                 signer: Signer=None,
                 signers: Dict[str, Signer]=None,
                 basedirpath: str=None):
        super().__init__(name,
                         nodeReg,
                         sovrinHa=sovrinHa,
                         p2pHa=p2pHa,
                         lastReqId=lastReqId,
                         signer=signer,
                         signers=signers,
                         basedirpath=basedirpath)
        stackargs = dict(name=name, ha=p2pHa, main=True, auto=AutoMode.always)
        self.peerStack = SimpleStack(stackargs, self.handlePeerMessage)
        # dataDir = "data/verifiers"
        # HasFileStorage.__init__(self,
        #                         name,
        #                         baseDir=basedirpath,
        #                         dataDir=dataDir)

        self.verifierStore = EntityFileStore(name=name,
                                             dataDir=self.getDataLocation())

    def handlePeerMessage(self, msg):
        pass
