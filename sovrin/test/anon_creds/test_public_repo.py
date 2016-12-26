import pytest

from anoncreds.protocol.issuer import Issuer
from anoncreds.protocol.repo.attributes_repo import AttributeRepoInMemory
from anoncreds.protocol.types import ClaimDefinition, ID
from anoncreds.protocol.wallet.issuer_wallet import IssuerWalletInMemory
from sovrin.anon_creds.sovrin_public_repo import SovrinPublicRepo
from sovrin.test.anon_creds.conftest import GVT


@pytest.fixture(scope="module")
def publicRepo(steward, stewardWallet):
    return SovrinPublicRepo(steward, stewardWallet)


@pytest.fixture(scope="module")
def issuerGvt(publicRepo):
    return Issuer(IssuerWalletInMemory('issuer1', publicRepo),
                  AttributeRepoInMemory())


@pytest.fixture(scope="module")
def claimDefGvt(stewardWallet):
    return ClaimDefinition('GVT', '1.0', GVT.attribNames(), 'CL',
                           stewardWallet.defaultId)


@pytest.fixture(scope="module")
def submittedClaimDefGvt(publicRepo, claimDefGvt, looper):
    return looper.run(publicRepo.submitClaimDef(claimDefGvt))


@pytest.fixture(scope="module")
def submittedClaimDefGvtID(submittedClaimDefGvt):
    return ID(claimDefKey=submittedClaimDefGvt.getKey(),
              claimDefId=submittedClaimDefGvt.seqId)


@pytest.fixture(scope="module")
def publicSecretKey(submittedClaimDefGvtID, issuerGvt, primes1, looper):
    return looper.run(
        issuerGvt._primaryIssuer.genKeys(submittedClaimDefGvtID, **primes1))


@pytest.fixture(scope="module")
def publicSecretRevocationKey(issuerGvt, looper):
    return looper.run(issuerGvt._nonRevocationIssuer.genRevocationKeys())


@pytest.fixture(scope="module")
def publicKey(publicSecretKey):
    return publicSecretKey[0]


@pytest.fixture(scope="module")
def publicRevocationKey(publicSecretRevocationKey):
    return publicSecretRevocationKey[0]


@pytest.fixture(scope="module")
def submittedPublicKeys(submittedClaimDefGvtID, publicRepo, publicSecretKey,
                        publicSecretRevocationKey, looper):
    pk, sk = publicSecretKey
    pkR, skR = publicSecretRevocationKey
    return looper.run(
        publicRepo.submitPublicKeys(id=submittedClaimDefGvtID, pk=pk, pkR=pkR))


@pytest.fixture(scope="module")
def submittedPublicKey(submittedPublicKeys):
    return submittedPublicKeys[0]


@pytest.fixture(scope="module")
def submittedPublicRevocationKey(submittedPublicKeys):
    return submittedPublicKeys[1]


def testSubmitClaimDef(submittedClaimDefGvt, claimDefGvt):
    assert submittedClaimDefGvt
    assert submittedClaimDefGvt.seqId
    submittedClaimDefGvt = submittedClaimDefGvt._replace(
        seqId=None)  # initial claim def didn't have seqNo
    assert submittedClaimDefGvt == claimDefGvt


def testGetClaimDef(submittedClaimDefGvt, publicRepo, looper):
    claimDef = looper.run(
        publicRepo.getClaimDef(ID(claimDefKey=submittedClaimDefGvt.getKey())))
    assert claimDef == submittedClaimDefGvt


def testSubmitPublicKey(submittedPublicKeys):
    assert submittedPublicKeys


def testGetPrimaryPublicKey(submittedClaimDefGvtID, submittedPublicKey,
                            publicRepo, looper):
    pk = looper.run(publicRepo.getPublicKey(id=submittedClaimDefGvtID))
    assert pk == submittedPublicKey


def testGetRevocationPublicKey(submittedClaimDefGvtID,
                               submittedPublicRevocationKey,
                               publicRepo, looper):
    pk = looper.run(
        publicRepo.getPublicKeyRevocation(id=submittedClaimDefGvtID))
    assert pk == submittedPublicRevocationKey
