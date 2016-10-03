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
from sovrin.client.wallet.cred_def import CredDef, IssuerPubKey
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
def addedIPV(looper, genned, addedSponsor, sponsor, sponsorWallet,
             issuerWallet, proverWallet, verifierWallet, issuerHA, proverHA,
             verifierHA):
    """
    Creating nyms for issuer, prover and verifier on Sovrin.
    """
    iNym = issuerWallet.defaultId
    pNym = proverWallet.defaultId
    vNym = verifierWallet.defaultId

    # DEPR
    # for nym, ha in ((iNym, issuerHA), (pNym, proverHA), (vNym, verifierHA)):
    #     addNym(ha, looper, nym, sponsNym, sponsor)

    for nym in (iNym, pNym, vNym):
        createNym(looper, nym, sponsor, sponsorWallet)


@pytest.fixture(scope="module")
def attrNames():
    return ["first_name", "last_name", "birth_date", "expire_date", \
           "undergrad", "postgrad"]


@pytest.fixture(scope="module")
def credDef(attrNames):
    # ip, port = genHa()
    return CredDefModule.CredDef(str(uuid.uuid4()), attrNames, name='name1',
                                 version='version1')


@pytest.fixture(scope="module")
def credDefSecretKeyAdded(genned, updatedSteward, addedSponsor, sponsor,
                              sponsorWallet, looper, tdir, nodeSet,
                          staticPrimes):
    csk = CredDefSecretKey(*staticPrimes.get("prime1"))
    return sponsorWallet.addCredDefSk(str(csk))


@pytest.fixture(scope="module")
def credentialDefinitionAdded(genned, updatedSteward, addedSponsor, sponsor,
                              sponsorWallet, looper, tdir, nodeSet, attrNames,
                              credDef, credDefSecretKeyAdded):
    old = sponsorWallet.pendingCount
    data = credDef.get(serFmt=SerFmt.base58)
    credDef = CredDef(seqNo=None,
                      attrNames=attrNames,
                      name=data[NAME],
                      version=data[VERSION],
                      origin=sponsorWallet.defaultId,
                      typ=data[TYPE],
                      secretKey=credDefSecretKeyAdded)
    pending = sponsorWallet.addCredDef(credDef)
    assert pending == old + 1
    reqs = sponsorWallet.preparePending()
    sponsor.submitReqs(*reqs)

    key = credDef.key()

    def chk():
        assert sponsorWallet.getCredDef(key).seqNo is not None

    looper.run(eventually(chk, retryWait=1, timeout=30))
    return sponsorWallet.getCredDef(key).seqNo


@pytest.fixture(scope="module")
def issuerSecretKeyAdded(genned, updatedSteward, addedSponsor, sponsor,
                              sponsorWallet, looper, tdir, nodeSet,
                          staticPrimes, credDefSecretKeyAdded,
                         credentialDefinitionAdded):
    csk = CredDefSecretKey.fromStr(sponsorWallet.getCredDefSk(credDefSecretKeyAdded))
    cd = sponsorWallet.getCredDef(seqNo=credentialDefinitionAdded)
    # This uid would be updated with the sequence number of the transaction
    # which writes the public key on Sovrin
    isk = IssuerSecretKey(cd, csk, uid=str(uuid.uuid4()))
    # TODO: Need to serialize it and then deserialize while doing get
    return sponsorWallet.addIssuerSecretKey(isk)


@pytest.fixture(scope="module")
def issuerPublicKeysAdded(genned, updatedSteward, addedSponsor, sponsor,
                              sponsorWallet, looper, tdir, nodeSet,
                          staticPrimes, credentialDefinitionAdded,
                          issuerSecretKeyAdded):
    isk = sponsorWallet.getIssuerSecretKey(issuerSecretKeyAdded)
    ipk = IssuerPubKey(N=isk.PK.N, R=isk.PK.R, S=isk.PK.S, Z=isk.PK.Z,
                       claimDefSeqNo=credentialDefinitionAdded,
                       secretKeyUid=isk.uid, origin=sponsorWallet.defaultId)
    sponsorWallet.addIssuerPublicKey(ipk)
    reqs = sponsorWallet.preparePending()
    # sponsor.registerObserver(sponsorWallet.handleIncomingReply)
    sponsor.submitReqs(*reqs)

    key = (sponsorWallet.defaultId, credentialDefinitionAdded)
    def chk():
        assert sponsorWallet.getIssuerPublicKey(key).seqNo is not None

    looper.run(eventually(chk, retryWait=1, timeout=30))
    return sponsorWallet.getIssuerPublicKey(key).seqNo
