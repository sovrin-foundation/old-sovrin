import asyncio
from typing import Any

from plenum.common.txn import NONCE, TYPE, NAME, VERSION, ORIGIN, IDENTIFIER, \
    DATA
from plenum.common.types import f
from plenum.common.util import getCryptonym

from anoncreds.protocol.prover import Prover
from anoncreds.protocol.types import ClaimDefinitionKey, ID, Claims, ProofInput
from anoncreds.protocol.utils import toDictWithStrValues
from sovrin.agent.msg_constants import REQUEST_CLAIM, CLAIM_PROOF, CLAIM_FIELD, \
    CLAIM_REQ_FIELD, PROOF_FIELD, PROOF_INPUT_FIELD, REVEALED_ATTRS_FIELD
from sovrin.client.wallet.link import ClaimProofRequest, Link
from sovrin.common.util import getNonceForProof


class AgentProver:
    def __init__(self, prover: Prover):
        self.prover = prover

    def sendReqClaim(self, link: Link, claimDefKey):
        if self.loop.is_running():
            self.loop.call_soon(asyncio.ensure_future,
                                self.sendReqClaimAsync(link, claimDefKey))
        else:
            self.loop.run_until_complete(
                self.sendReqClaimAsync(link, claimDefKey))

    async def sendReqClaimAsync(self, link: Link, claimDefKey):
        name, version, origin = claimDefKey
        claimDefKey = ClaimDefinitionKey(name, version, origin)

        claimReq = await self.prover.createClaimRequest(claimDefId=ID(
            claimDefKey), proverId=link.invitationNonce,
            reqNonRevoc=False)

        op = {
            NONCE: link.invitationNonce,
            TYPE: REQUEST_CLAIM,
            NAME: name,
            VERSION: version,
            ORIGIN: origin,
            CLAIM_REQ_FIELD: claimReq.toStrDict()
        }

        self.signAndSend(msg=op, linkName=link.name)

    async def handleReqClaimResponse(self, msg):
        body, _ = msg
        issuerId = body.get(IDENTIFIER)
        claim = body[DATA]
        li = self._getLinkByTarget(getCryptonym(issuerId))
        if li:
            self.notifyResponseFromMsg(li.name, body.get(f.REQ_ID.nm))
            self.notifyMsgListener('    Received claim "{}".\n'.format(
                claim[NAME]))
            name, version, claimAuthor = \
                claim[NAME], claim[VERSION], claim[f.IDENTIFIER.nm]

            claimDefKey = ClaimDefinitionKey(name, version, claimAuthor)
            claimDef = await self.prover.wallet.getClaimDef(ID(claimDefKey))
            claimDefId = ID(claimDefKey=claimDefKey, claimDefId=claimDef.seqId)

            claim = Claims.fromStrDict(claim[CLAIM_FIELD])

            await self.prover.processClaim(claimDefId, claim)
        else:
            self.notifyMsgListener("No matching link found")

    def sendProof(self, link: Link, claimPrfReq: ClaimProofRequest):
        if self.loop.is_running():
            self.loop.call_soon(asyncio.ensure_future,
                                self.sendProofAsync(link, claimPrfReq))
        else:
            self.loop.run_until_complete(self.sendProofAsync(link, claimPrfReq))

    async def sendProofAsync(self, link: Link, claimPrfReq: ClaimProofRequest):
        nonce = getNonceForProof(link.invitationNonce)

        revealedAttrNames = claimPrfReq.verifiableAttributes
        proofInput = ProofInput(revealedAttrs=revealedAttrNames)
        proof, revealedAttrs = await self.prover.presentProof(proofInput, nonce)

        op = {
            NAME: claimPrfReq.name,
            VERSION: claimPrfReq.version,
            NONCE: link.invitationNonce,
            TYPE: CLAIM_PROOF,
            PROOF_FIELD: proof.toStrDict(),
            PROOF_INPUT_FIELD: proofInput.toStrDict(),
            REVEALED_ATTRS_FIELD: toDictWithStrValues(revealedAttrs)
        }

        self.signAndSend(msg=op, linkName=link.name)

    def handleProofStatusResponse(self, msg: Any):
        body, _ = msg
        data = body.get(DATA)
        identifier = body.get(IDENTIFIER)
        li = self._getLinkByTarget(getCryptonym(identifier))
        self.notifyResponseFromMsg(li.name, body.get(f.REQ_ID.nm))
        self.notifyMsgListener(data)

    async def getMatchingLinksWithReceivedClaimAsync(self, claimName=None):
        matchingLinkAndAvailableClaim = self.wallet.getMatchingLinksWithAvailableClaim(
            claimName)
        matchingLinkAndReceivedClaim = []
        for li, cl in matchingLinkAndAvailableClaim:
            name, version, origin = cl
            claimDefKeyId = ID(
                ClaimDefinitionKey(name=name, version=version, issuerId=origin))
            claimDef = await self.prover.wallet.getClaimDef(claimDefKeyId)
            claimAttrs = set(claimDef.attrNames)
            claim = None
            try:
                claim = await self.prover.wallet.getClaims(claimDefKeyId)
            except ValueError:
                pass  # it means no claim was issued
            attrs = {k: None for k in claimAttrs}
            if claim:
                issuedAttributes = claim.primaryClaim.attrs
                if claimAttrs.intersection(issuedAttributes.keys()):
                    attrs = {k: issuedAttributes[k] for k in claimAttrs}
            matchingLinkAndReceivedClaim.append((li, cl, attrs))
        return matchingLinkAndReceivedClaim

    async def getMatchingRcvdClaimsAsync(self, attributes):
        linksAndReceivedClaim = await self.getMatchingLinksWithReceivedClaimAsync()
        attributes = set(attributes)

        matchingLinkAndRcvdClaim = []
        for li, cl, issuedAttrs in linksAndReceivedClaim:
            if attributes.intersection(issuedAttrs.keys()):
                matchingLinkAndRcvdClaim.append((li, cl, issuedAttrs))
        return matchingLinkAndRcvdClaim
