import pytest
import sovrin.anon_creds.cred_def as CredDefModule
from plenum.common.txn import NAME, VERSION, TYPE, IP, PORT, KEYS
from plenum.test.eventually import eventually
from plenum.test.helper import genHa
from sovrin.client.wallet.cred_def import CredDef
from sovrin.client.wallet.cred_def import CredDefKey
from sovrin.common.util import getConfig
from sovrin.test.helper import createNym, _newWallet

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
    return "first_name", "last_name", "birth_date", "expire_date", \
           "undergrad", "postgrad"


@pytest.fixture(scope="module")
def credDef(attrNames):
    ip, port = genHa()
    return CredDefModule.CredDef(attrNames, 'name1', 'version1',
                                 p_prime="prime1", q_prime="prime1",
                                 ip=ip, port=port)


@pytest.fixture(scope="module")
def credentialDefinitionAdded(genned, updatedSteward, addedSponsor, sponsor,
                              sponsorWallet, looper, tdir, nodeSet, credDef):
    old = sponsorWallet.pendingCount
    data = credDef.get(serFmt=CredDefModule.SerFmt.base58)
    credDef = CredDef(data[NAME], data[VERSION],
                      sponsorWallet.defaultId, data[TYPE],
                      data[IP], data[PORT], data[KEYS])
    pending = sponsorWallet.addCredDef(credDef)
    assert pending == old + 1
    reqs = sponsorWallet.preparePending()
    # sponsor.registerObserver(sponsorWallet.handleIncomingReply)
    sponsor.submitReqs(*reqs)

    key = CredDefKey(*credDef.key())

    def chk():
        assert sponsorWallet.getCredDef(key).seqNo is not None

    looper.run(eventually(chk, retryWait=1, timeout=15))
    return sponsorWallet.getCredDef(key).seqNo

    # DEPR
    # op = {
    #     TXN_TYPE: CRED_DEF,
    #     DATA: data
    # }
    # return submitAndCheck(looper, sponsor, sponsorWallet, op)
