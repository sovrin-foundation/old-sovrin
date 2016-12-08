from typing import Any

from anoncreds.protocol.types import FullProof
from anoncreds.protocol.types import ProofInput
from anoncreds.protocol.utils import fromDictWithStrValues
from anoncreds.protocol.verifier import Verifier
from plenum.common.txn import NAME, NONCE, TYPE, DATA, VERSION
from plenum.common.types import f

from sovrin.agent.msg_types import CLAIM_PROOF_STATUS
from sovrin.common.util import getNonceForProof


class AgentVerifier(Verifier):
    def __init__(self, verifier: Verifier):
        self.verifier = verifier

    def verifyClaimProof(self, msg: Any):
        body, (frm, ha) = msg
        link = self.verifyAndGetLink(msg)
        if not link:
            raise NotImplementedError

        claimName = body[NAME]
        nonce = nonce = getNonceForProof(body[NONCE])
        proof = FullProof.fromStrDict(body['proof'])
        proofInput = ProofInput.fromStrDict(body['proofInput'])
        revealedAttrs = fromDictWithStrValues(body['revealedAttrs'])

        result = self.verifier.verify(proofInput, proof, revealedAttrs, nonce)

        status = 'verified' if result else 'failed verification'
        resp = {
            TYPE: CLAIM_PROOF_STATUS,
            DATA: '    Your claim {} {} was received and {}\n'.
                format(body[NAME], body[VERSION], status),
        }
        self.signAndSend(resp, link.localIdentifier, frm,
                         origReqId=body.get(f.REQ_ID.nm))

        if result:
            self._postClaimVerif(claimName, link, frm)
