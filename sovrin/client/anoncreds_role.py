from typing import Dict, Union, Tuple

from plenum.client.signer import Signer
from plenum.common.types import HA
from plenum.common.util import getlogger

from sovrin.client.client import Client


logger = getlogger()


# TODO Rename to HasAnonCreds if appropriate.
class AnonCredsRole:
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
        self.peerStack = None

    def start(self, loop):
        if self.peerStack:
            self.peerStack.start()
        else:
            logger.error("Peer stack not initialized")

    async def prod(self, limit) -> int:
        c = await self.client.prod(limit=limit)
        if self.peerStack:
            return c + await self.peerStack.service(limit)
        else:
            logger.error("Peer stack not initialized")
