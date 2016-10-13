import uuid

import pytest
import sovrin.anon_creds.cred_def as CredDefModule
from anoncreds.protocol.cred_def_secret_key import CredDefSecretKey
from anoncreds.protocol.issuer_secret_key import IssuerSecretKey
from anoncreds.protocol.types import SerFmt
from plenum.common.txn import NAME, VERSION, TYPE, IP, PORT, KEYS
from plenum.common.util import randomString
from plenum.test.eventually import eventually
from plenum.test.helper import genHa
from sovrin.client.wallet.claim_def import ClaimDef, IssuerPubKey
from sovrin.common.util import getConfig
from sovrin.test.helper import createNym, _newWallet

# noinspection PyUnresolvedReferences
from anoncreds.test.conftest import staticPrimes

# TODO Make a fixture for creating a client with a anon-creds features
#  enabled.

config = getConfig()


@pytest.fixture(scope="module")
def issuerWallet():
    return _newWallet()


@pytest.fixture(scope="module")
def proverWallet():
    return _newWallet()


@pytest.fixture(scope="module")
def verifierWallet():
    return _newWallet()


@pytest.fixture(scope="module")
def issuerHA():
    return genHa()


@pytest.fixture(scope="module")
def proverHA():
    return genHa()


@pytest.fixture(scope="module")
def verifierHA():
    return genHa()


@pytest.fixture(scope="module")
def proverAttributeNames():
    return sorted(['name', 'age', 'sex', 'country'])


@pytest.fixture(scope="module")
def proverAttributes():
    return {'name': 'Mario', 'age': '25', 'sex': 'Male', 'country': 'Italy'}


@pytest.fixture(scope="module")
def addedIPV(looper, nodeSet, addedSponsor, sponsor, sponsorWallet,
             issuerWallet, proverWallet, verifierWallet, issuerHA, proverHA,
             verifierHA):
    """
    Creating nyms for issuer, prover and verifier on Sovrin.
    """
    iNym = issuerWallet.defaultId
    pNym = proverWallet.defaultId
    vNym = verifierWallet.defaultId

    for nym in (iNym, pNym, vNym):
        createNym(looper, nym, sponsor, sponsorWallet)


@pytest.fixture(scope="module")
def attrNames():
    return ["first_name", "last_name", "birth_date", "expire_date",
            "undergrad", "postgrad"]


@pytest.fixture(scope="module")
def claimDef(attrNames):
    return CredDefModule.CredDef(str(uuid.uuid4()), attrNames, name='name1',
                                 version='version1')


@pytest.fixture(scope="module")
def claimDefSecretKeyAdded(nodeSet, steward, addedSponsor, sponsor,
                              sponsorWallet, looper, tdir,
                          staticPrimes):
    csk = CredDefSecretKey(*staticPrimes.get("prime1"))
    return sponsorWallet.addClaimDefSk(str(csk))


@pytest.fixture(scope="module")
def claimDefinitionAdded(nodeSet, steward, addedSponsor, sponsor,
                         sponsorWallet, looper, tdir, attrNames,
                         claimDef, claimDefSecretKeyAdded):
    old = sponsorWallet.pendingCount
    data = claimDef.get(serFmt=SerFmt.base58)
    claimDef = ClaimDef(seqNo=None,
                        attrNames=attrNames,
                        name=data[NAME],
                        version=data[VERSION],
                        origin=sponsorWallet.defaultId,
                        typ=data[TYPE],
                        secretKey=claimDefSecretKeyAdded)
    pending = sponsorWallet.addClaimDef(claimDef)
    assert pending == old + 1
    reqs = sponsorWallet.preparePending()
    sponsor.submitReqs(*reqs)

    key = claimDef.key

    def chk():
        assert sponsorWallet.getClaimDef(key).seqNo is not None

    looper.run(eventually(chk, retryWait=1, timeout=30))
    return sponsorWallet.getClaimDef(key).seqNo


@pytest.fixture(scope="module")
def issuerSecretKeyAdded(nodeSet, steward, addedSponsor, sponsor,
                              sponsorWallet, looper, tdir,
                          staticPrimes, claimDefSecretKeyAdded,
                         claimDefinitionAdded):
    csk = CredDefSecretKey.fromStr(sponsorWallet.getClaimDefSk(claimDefSecretKeyAdded))
    cd = sponsorWallet.getClaimDef(seqNo=claimDefinitionAdded)
    # This uid would be updated with the sequence number of the transaction
    # which writes the public key on Sovrin
    isk = IssuerSecretKey(cd, csk, uid=str(uuid.uuid4()))
    # TODO: Need to serialize it and then deserialize while doing get
    return sponsorWallet.addIssuerSecretKey(isk)


@pytest.fixture(scope="module")
def issuerPublicKeysAdded(nodeSet, steward, addedSponsor, sponsor,
                              sponsorWallet, looper, tdir,
                          staticPrimes, claimDefinitionAdded,
                          issuerSecretKeyAdded):
    isk = sponsorWallet.getIssuerSecretKey(issuerSecretKeyAdded)
    ipk = IssuerPubKey(N=isk.PK.N, R=isk.PK.R, S=isk.PK.S, Z=isk.PK.Z,
                       claimDefSeqNo=claimDefinitionAdded,
                       secretKeyUid=isk.uid, origin=sponsorWallet.defaultId)
    sponsorWallet.addIssuerPublicKey(ipk)
    reqs = sponsorWallet.preparePending()
    sponsor.submitReqs(*reqs)

    key = (sponsorWallet.defaultId, claimDefinitionAdded)

    def chk():
        assert sponsorWallet.getIssuerPublicKey(key).seqNo is not None

    looper.run(eventually(chk, retryWait=1, timeout=30))
    return sponsorWallet.getIssuerPublicKey(key).seqNo
