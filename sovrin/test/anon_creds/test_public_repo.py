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
def submittedClaimDefGvt(publicRepo, claimDefGvt):
    return publicRepo.submitClaimDef(claimDefGvt)


@pytest.fixture(scope="module")
def submittedClaimDefGvtID(submittedClaimDefGvt):
    return ID(claimDefKey=submittedClaimDefGvt.getKey(), claimDefId=submittedClaimDefGvt.id)


@pytest.fixture(scope="module")
def submittedPublicKey(submittedClaimDefGvtID, publicRepo, issuerGvt, primes1):
    pk, sk = issuerGvt._primaryIssuer.genKeys(submittedClaimDefGvtID, **primes1)
    publicRepo.submitPublicKeys(id=submittedClaimDefGvtID, pk=pk)


def testSubmitClaimDef(submittedClaimDefGvt, stewardWallet):
    assert submittedClaimDefGvt
    assert submittedClaimDefGvt.id
    assert submittedClaimDefGvt.issuerId == stewardWallet.defaultId
    assert submittedClaimDefGvt.name == 'GVT'
    assert submittedClaimDefGvt.version == '1.0'
    assert submittedClaimDefGvt.type == 'CL'
    assert submittedClaimDefGvt.attrNames == ['name', 'age', 'height', 'sex']


def testGetClaimDef(claimDefGvt, publicRepo, stewardWallet):
    claimDef = publicRepo.getClaimDef(ID(claimDefKey=claimDefGvt.getKey()))
    assert claimDef
    assert claimDef.id
    assert claimDef.issuerId == stewardWallet.defaultId
    assert claimDef.name == 'GVT'
    assert claimDef.version == '1.0'
    assert claimDef.type == 'CL'
    assert claimDef.attrNames == ['name', 'age', 'height', 'sex']


def testSubmitPublicKey(submittedPublicKey):
    pass


def testGetPublicKey(submittedClaimDefGvtID, submittedPublicKey, publicRepo):
    pk = publicRepo.getPublicKey(id=submittedClaimDefGvtID)
    assert pk
