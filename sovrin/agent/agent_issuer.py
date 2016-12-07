from anoncreds.protocol.issuer import Issuer
from anoncreds.protocol.types import ClaimDefinitionKey, ID
from anoncreds.protocol.types import ClaimRequest
from plenum.common.txn import NAME, VERSION, ORIGIN
from plenum.common.types import f

from sovrin.agent.constants import EVENT_NOTIFY_MSG
from sovrin.agent.msg_types import CLAIM


class AgentIssuer:
    def __init__(self, issuer: Issuer):
        self.issuer = issuer

    def processReqClaim(self, msg):
        body, (frm, ha) = msg
        link = self.verifyAndGetLink(msg)
        if not link:
            raise NotImplementedError
        name = body[NAME]
        if not self.isClaimAvailable(link, name):
            self.notifyToRemoteCaller(
                EVENT_NOTIFY_MSG, "This claim is not yet available",
                self.issuer.wallet.defaultId, frm, origReqId=body.get(f.REQ_ID.nm))
            return

        version = body[VERSION]
        origin = body[ORIGIN]
        claimReq = ClaimRequest.fromStrDict(body['claimReq'])

        claimDefKey = ClaimDefinitionKey(name, version, origin)
        claimDef = self.issuer.wallet.getClaimDef(ID(claimDefKey))
        claimDefId = ID(claimDefKey=claimDefKey, claimDefId=claimDef.id)

        claim = self.issuer.issueClaim(claimDefId, claimReq)

        claimDetails = {
            NAME: claimDef.name,
            VERSION: claimDef.version,
            'claim': claim.toStrDict(),
            f.IDENTIFIER.nm: claimDef.origin
        }

        resp = self.getCommonMsg(CLAIM, claimDetails)
        self.signAndSend(resp, link.localIdentifier, frm,
                         origReqId=body.get(f.REQ_ID.nm))
