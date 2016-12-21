import pytest

from anoncreds.protocol.issuer import Issuer
from anoncreds.protocol.repo.attributes_repo import AttributeRepoInMemory
from anoncreds.protocol.types import ClaimDefinition, ID
from anoncreds.protocol.wallet.issuer_wallet import IssuerWalletInMemory
from sovrin.anon_creds.sovrin_public_repo import SovrinPublicRepo
from sovrin.test.anon_creds.conftest import GVT


@pytest.fixture(scope="module")
def publicRepo(looper, steward, stewardWallet):
    return SovrinPublicRepo(looper, steward, stewardWallet)


@pytest.fixture(scope="module")
def issuerGvt(publicRepo):
    return Issuer(IssuerWalletInMemory('issuer1', publicRepo), AttributeRepoInMemory())


@pytest.fixture(scope="module")
def claimDefGvt(stewardWallet):
    return ClaimDefinition('GVT', '1.0', GVT.attribNames(), 'CL', stewardWallet.defaultId)


@pytest.fixture(scope="module")
def submittedClaimDefGvt(publicRepo, claimDefGvt, looper):
    return looper.run(publicRepo.submitClaimDef(claimDefGvt))


@pytest.fixture(scope="module")
def submittedClaimDefGvtID(submittedClaimDefGvt):
    return ID(claimDefKey=submittedClaimDefGvt.getKey(), claimDefId=submittedClaimDefGvt.id)


@pytest.fixture(scope="module")
def publicSecretKey(submittedClaimDefGvtID, issuerGvt, primes1, looper):
    return looper.run(issuerGvt._primaryIssuer.genKeys(submittedClaimDefGvtID, **primes1))


@pytest.fixture(scope="module")
def publicKey(publicSecretKey):
    return publicSecretKey[0]


@pytest.fixture(scope="module")
def submittedPublicKey(submittedClaimDefGvtID, publicRepo, publicSecretKey, looper):
    pk, sk = publicSecretKey
    looper.run(publicRepo.submitPublicKeys(id=submittedClaimDefGvtID, pk=pk))


def testSubmitClaimDef(submittedClaimDefGvt, claimDefGvt):
    assert submittedClaimDefGvt
    assert submittedClaimDefGvt.name == claimDefGvt.name
    assert submittedClaimDefGvt.version == claimDefGvt.version
    assert submittedClaimDefGvt.attrNames == claimDefGvt.attrNames
    assert submittedClaimDefGvt.type == claimDefGvt.type
    assert submittedClaimDefGvt.issuerId == claimDefGvt.issuerId


def testGetClaimDef(submittedClaimDefGvt, publicRepo, looper):
    claimDef = looper.run(publicRepo.getClaimDef(ID(claimDefKey=submittedClaimDefGvt.getKey())))
    assert claimDef == submittedClaimDefGvt


def testSubmitPublicKey(submittedPublicKey):
    pass


def testGetPublicKey(submittedClaimDefGvtID, submittedPublicKey, publicRepo, publicKey, looper):
    pk = looper.run(publicRepo.getPublicKey(id=submittedClaimDefGvtID))
    assert pk == publicKey
