from typing import Any

from anoncreds.protocol.prover import Prover
from anoncreds.protocol.types import ClaimDefinitionKey, ID, Claims, ProofInput
from anoncreds.protocol.utils import toDictWithStrValues
from plenum.common.txn import NONCE, TYPE, NAME, VERSION, ORIGIN, IDENTIFIER, DATA
from plenum.common.types import f
from plenum.common.util import getCryptonym

from sovrin.agent.msg_types import REQUEST_CLAIM, CLAIM_PROOF
from sovrin.client.wallet.link import ClaimProofRequest, Link
from sovrin.common.util import getNonceForProof


class AgentProver:
    def __init__(self, prover: Prover):
        self.prover = prover

    def sendReqClaim(self, link: Link, claimDefKey):
        name, version, origin = claimDefKey
        claimDefKey = ClaimDefinitionKey(name, version, origin)

        claimReq = self.prover.createClaimRequest(id=ID(claimDefKey), reqNonRevoc=False)

        op = {
            NONCE: link.invitationNonce,
            TYPE: REQUEST_CLAIM,
            NAME: name,
            VERSION: version,
            ORIGIN: origin,
            'claimReq': claimReq.toStrDict()
        }

        self.signAndSend(msg=op, linkName=link.name)

    def handleReqClaimResponse(self, msg):
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
            claimDef = self.prover.wallet.getClaimDef(ID(claimDefKey))
            claimDefId = ID(claimDefKey=claimDefKey, claimDefId=claimDef.id)

            claim = Claims.fromStrDict(claim['claim'])

            self.prover.processClaim(claimDefId, claim)
        else:
            self.notifyMsgListener("No matching link found")

    def sendProof(self, link: Link, claimPrfReq: ClaimProofRequest):
        nonce = getNonceForProof(link.invitationNonce)
        self.logger.debug("Building proof using {} for {}".
                          format(claimPrfReq, link))

        revealedAttrNames = list(claimPrfReq.attributes.keys())
        proofInput = ProofInput(revealedAttrs=revealedAttrNames)
        proof, revealedAttrs = self.prover.presentProof(proofInput, nonce)
        self.logger.debug("Prepared proof {}".format(proof))

        op = {
            NAME: claimPrfReq.name,
            VERSION: claimPrfReq.version,
            NONCE: link.invitationNonce,
            TYPE: CLAIM_PROOF,
            'proof': proof.toStrDict(),
            'proofInput': proofInput.toStrDict(),
            'revealedAttrs': toDictWithStrValues(revealedAttrs)
        }

        self.signAndSend(msg=op, linkName=link.name)

    def handleProofStatusResponse(self, msg: Any):
        body, _ = msg
        data = body.get(DATA)
        identifier = body.get(IDENTIFIER)
        li = self._getLinkByTarget(getCryptonym(identifier))
        self.notifyResponseFromMsg(li.name, body.get(f.REQ_ID.nm))
        self.notifyMsgListener(data)
