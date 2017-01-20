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
def issuer(steward, stewardWallet, attrRepo):
    return SovrinIssuer(steward, stewardWallet, attrRepo)


@pytest.fixture(scope="module")
def prover(userClientA, userWalletA):
    return SovrinProver(userClientA, userWalletA)


@pytest.fixture(scope="module")
def verifier(userClientB, userWalletB):
    return SovrinVerifier(userClientB, userWalletB)


def testAnonCredsPrimaryOnly(issuer, prover, verifier, attrRepo, primes1, looper):
    async def doTestAnonCredsPrimaryOnly():
        # 1. Create a Claim Def
        claimDef = await issuer.genClaimDef('GVT', '1.0', GVT.attribNames())
        claimDefId = ID(claimDefKey=claimDef.getKey(),
                        claimDefId=claimDef.seqId)

        # 2. Create keys for the Claim Def
        await issuer.genKeys(claimDefId, **primes1)

        # 3. Issue accumulator
        await issuer.issueAccumulator(claimDefId=claimDefId, iA='110', L=5)

        # 4. set attributes for user1
        attrs = GVT.attribs(name='Alex', age=28, height=175, sex='male')
        proverId = str(prover.proverId)
        attrRepo.addAttributes(claimDef.getKey(), proverId, attrs)

        # 5. request Claims
        claimsReq = await prover.createClaimRequest(claimDefId, proverId, False)
        claims = await issuer.issueClaim(claimDefId, claimsReq)
        await prover.processClaim(claimDefId, claims)

        # 6. proof Claims
        proofInput = ProofInput(
            ['name'],
            [PredicateGE('age', 18)])

        nonce = verifier.generateNonce()
        proof, revealedAttrs = await prover.presentProof(proofInput, nonce)
        assert await verifier.verify(proofInput, proof, revealedAttrs, nonce)

    looper.run(doTestAnonCredsPrimaryOnly)
