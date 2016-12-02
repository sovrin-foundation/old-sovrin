import pytest
from anoncreds.protocol.repo.attributes_repo import AttributeRepoInMemory
from anoncreds.protocol.types import ID, ProofInput, PredicateGE

from sovrin.anon_creds.sovrin_issuer import SovrinIssuer
from sovrin.anon_creds.sovrin_prover import SovrinProver
from sovrin.anon_creds.sovrin_verifier import SovrinVerifier
from sovrin.test.anon_creds.conftest import GVT


@pytest.fixture(scope="module")
def attrRepo():
    return AttributeRepoInMemory()


@pytest.fixture(scope="module")
def issuer(looper, steward, stewardWallet, attrRepo):
    return SovrinIssuer(looper, steward, stewardWallet, attrRepo)


@pytest.fixture(scope="module")
def prover(looper, userClientA, userWalletA):
    return SovrinProver(looper, userClientA, userWalletA)


@pytest.fixture(scope="module")
def verifier(looper, userClientB, userWalletB):
    return SovrinVerifier(looper, userClientB, userWalletB)


def testAnonCreds(issuer, prover, verifier, attrRepo, primes1):
    # 1. Create a Claim Def
    claimDef = issuer.genClaimDef('GVT', '1.0', GVT.attribNames())
    claimDefId = ID(claimDefKey=claimDef.getKey(), claimDefId=claimDef.id)

    # 2. Create keys for the Claim Def
    issuer.genKeys(claimDefId, **primes1)

    # 3. Issue accumulator
    issuer.issueAccumulator(id=claimDefId, iA='110', L=5)

    # 4. set attributes for user1
    attrs = GVT.attribs(name='Alex', age=28, height=175, sex='male')
    attrRepo.addAttributes(claimDef.getKey(), prover.id, attrs)

    # 5. request Claims
    claimsReq = prover.createClaimRequest(claimDefId, False)
    claims = issuer.issueClaim(claimDefId, claimsReq)
    prover.processClaim(claimDefId, claims)

    # 6. proof Claims
    proofInput = ProofInput(
        ['name'],
        [PredicateGE('age', 18)])

    nonce = verifier.generateNonce()
    proof = prover.presentProof(proofInput, nonce)
    revealedAttrs = attrRepo.getRevealedAttributesForProver(prover, proofInput.revealedAttrs).encoded()
    assert verifier.verify(proofInput, proof, revealedAttrs, nonce)
