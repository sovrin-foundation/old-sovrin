import asyncio
from anoncreds.protocol.types import ClaimDefinitionKey, ID
from plenum.test.eventually import eventually


def testAnonCreds(aliceAgent, aliceAcceptedFaber, faberAgent, aliceAcceptedAcme, acmeAgent, emptyLooper):
    # 1. request Claims from Faber
    faberLink = aliceAgent.wallet.getLink('Faber College')
    name, version, origin = faberLink.availableClaims[0]
    claimDefKey = ClaimDefinitionKey(name, version, origin)
    cd = acmeAgent.verifier._wallet.getClaimDef(ID(claimDefKey))
    pk = acmeAgent.verifier._wallet.getPublicKey(ID(claimDefKey))
    aliceAgent.sendReqClaim(faberLink, claimDefKey)

    # 2. check that claim is received from Faber
    def chkClaims():
        assert aliceAgent.prover.wallet.getClaims(ID(claimDefKey))

    emptyLooper.run(eventually(chkClaims, timeout=20))

    # 3. send claim proof to Acme
    acmeLink, acmeClaimPrfReq = aliceAgent.wallet.getMatchingLinksWithClaimReq("Job-Application", "Acme Corp")[0]
    aliceAgent.sendProof(acmeLink, acmeClaimPrfReq)

    # 4. check that claim proof is verified by Acme
    def chkProof():
        internalId = acmeAgent.getInternalIdByInvitedNonce(acmeLink.invitationNonce)
        link = acmeAgent.wallet.getLinkByInternalId(internalId)
        assert len(link.verifiedClaimProofs) >= 1

    emptyLooper.run(eventually(chkProof, timeout=20))
