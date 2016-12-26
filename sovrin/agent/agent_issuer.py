from abc import abstractmethod
from typing import Dict, Any

from plenum.common.txn import NAME, VERSION, ORIGIN
from plenum.common.types import f

from anoncreds.protocol.issuer import Issuer
from anoncreds.protocol.types import ClaimDefinitionKey, ID
from anoncreds.protocol.types import ClaimRequest
from sovrin.agent.constants import EVENT_NOTIFY_MSG
from sovrin.agent.msg_constants import CLAIM, CLAIM_REQ_FIELD, CLAIM_FIELD


class AgentIssuer:
    def __init__(self, issuer: Issuer):
        self.issuer = issuer

    async def processReqClaim(self, msg):
        body, (frm, ha) = msg
        link = self.verifyAndGetLink(msg)
        if not link:
            raise NotImplementedError
        name = body[NAME]
        if not self.isClaimAvailable(link, name):
            self.notifyToRemoteCaller(
                EVENT_NOTIFY_MSG, "This claim is not yet available",
                self.issuer.wallet.defaultId, frm,
                origReqId=body.get(f.REQ_ID.nm))
            return

        version = body[VERSION]
        origin = body[ORIGIN]
        claimReq = ClaimRequest.fromStrDict(body[CLAIM_REQ_FIELD])

        claimDefKey = ClaimDefinitionKey(name, version, origin)
        claimDef = await self.issuer.wallet.getClaimDef(ID(claimDefKey))
        claimDefId = ID(claimDefKey=claimDefKey, claimDefId=claimDef.seqId)

        self._addAtrribute(claimDefKey=claimDefKey, proverId=claimReq.userId,
                           link=link)

        claim = await self.issuer.issueClaim(claimDefId, claimReq)

        claimDetails = {
            NAME: claimDef.name,
            VERSION: claimDef.version,
            CLAIM_FIELD: claim.toStrDict(),
            f.IDENTIFIER.nm: claimDef.issuerId
        }

        resp = self.getCommonMsg(CLAIM, claimDetails)
        self.signAndSend(resp, link.localIdentifier, frm,
                         origReqId=body.get(f.REQ_ID.nm))

    @abstractmethod
    def _addAtrribute(self, claimDefKey, proverId, link) -> Dict[str, Any]:
        raise NotImplementedError
