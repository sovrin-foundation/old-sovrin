from typing import Dict, Union, Tuple

from raet.raeting import AutoMode

from plenum.client.signer import Signer
from plenum.common.stacked import SimpleStack
from plenum.common.types import HA
from anoncreds.protocol.issuer import Issuer as IssuerObj

from sovrin.client.anoncreds_client import AnoncredsClient
from sovrin.client.client import Client as SovrinClient


class Issuer(AnoncredsClient):
    def __init__(self,
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

    def handlePeerMessage(self, msg):
        pass