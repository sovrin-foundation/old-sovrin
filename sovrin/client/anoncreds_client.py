from typing import Dict, Union, Tuple

from plenum.client.signer import Signer
from plenum.common.types import HA
from plenum.common.util import getlogger

from sovrin.client.client import Client as SovrinClient


logger = getlogger()


class AnoncredsClient:
    def __init__(self,
                 name: str,
                 nodeReg: Dict[str, HA] = None,
                 sovrinHa: Union[HA, Tuple[str, int]] = None,
                 p2pHa: Union[HA, Tuple[str, int]] = None,
                 lastReqId: int = 0,
                 signer: Signer = None,
                 signers: Dict[str, Signer] = None,
                 basedirpath: str = None):
        self.sovrinClient = SovrinClient(name, nodeReg, ha=sovrinHa,
                                         lastReqId=lastReqId, signer=signer,
                                         signers=signers,
                                         basedirpath=basedirpath)
        self.peerStack = None

    def start(self, loop):
        self.sovrinClient.start(loop)
        if self.peerStack:
            self.peerStack.start()
        else:
            logger.error("Peer stack not initialised")

    async def prod(self, limit) -> int:
        await self.sovrinClient.prod(limit=limit)