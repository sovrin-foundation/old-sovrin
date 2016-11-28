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
def claimDefGvt():
    return ClaimDefinition('GVT', '1.0', GVT.attribNames(), 'CL', 11)


@pytest.fixture(scope="module")
def submittedClaimDefGvt(publicRepo, claimDefGvt):
    return publicRepo.submitClaimDef(claimDefGvt)


@pytest.fixture(scope="module")
def submittedPublicKey(submittedClaimDefGvt, publicRepo, claimDefGvt, issuerGvt, primes1):
    id = ID(claimDefKey=claimDefGvt.getKey(), claimDefId=claimDefGvt.id)
    pk, sk = issuerGvt._primaryIssuer.genKeys(id, **primes1)
    publicRepo.submitPublicKeys(id=id, pk=pk)


def testSubmitClaimDef(submittedClaimDefGvt):
    assert submittedClaimDefGvt
    assert submittedClaimDefGvt.id
    assert submittedClaimDefGvt.issuerId
    assert submittedClaimDefGvt.name == 'GVT'
    assert submittedClaimDefGvt.version == '1.0'
    assert submittedClaimDefGvt.type == 'CL'
    assert submittedClaimDefGvt.attrNames == ['name', 'age', 'height', 'sex']


def testGetClaimDef(claimDefGvt, submittedClaimDefGvt, publicRepo):
    claimDef = publicRepo.getClaimDef(ID(claimDefGvt.getKey()))
    assert claimDef
    assert claimDef.id
    assert claimDef.issuerId
    assert claimDef.name == 'GVT'
    assert claimDef.version == '1.0'
    assert claimDef.type == 'CL'
    assert claimDef.attrNames == ['name', 'age', 'height', 'sex']


def testSubmitPublicKey(submittedPublicKey):
    pass


def testGetPublicKey(claimDefGvt, submittedPublicKey, publicRepo):
    id = ID(claimDefKey=claimDefGvt.getKey(), claimDefId=claimDefGvt.id)
    pk = publicRepo.getPublicKey(id=id)
    assert pk
