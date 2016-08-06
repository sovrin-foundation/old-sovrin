import json

import pytest

from anoncreds.protocol.types import SerFmt
from anoncreds.protocol.utils import encodeAttrs

from plenum.client.signer import SimpleSigner

from plenum.test.helper import genHa
from anoncreds.protocol.credential_definition import CredentialDefinition
from anoncreds.temp_primes import P_PRIME1, Q_PRIME1
from sovrin.test.helper import addNym

from plenum.common.txn import TXN_TYPE, DATA

from sovrin.common.txn import CRED_DEF
from sovrin.test.helper import submitAndCheck


# TODO Make a fixture for creating a client with a anon-creds features
#  enabled.
@pytest.fixture(scope="module")
def issuerSigner():
    signer = SimpleSigner()
    return signer


@pytest.fixture(scope="module")
def proverSigner():
    signer = SimpleSigner()
    return signer


@pytest.fixture(scope="module")
def verifierSigner():
    signer = SimpleSigner()
    return signer


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
def encodedProverAttributes(proverAttributes):
    return encodeAttrs(proverAttributes)


@pytest.fixture(scope="module")
def addedIPV(looper, genned, addedSponsor, sponsor, sponsorSigner,
             issuerSigner, proverSigner, verifierSigner, issuerHA, proverHA,
             verifierHA):
    """
    Creating nyms for issuer, prover and verifier on Sovrin.
    """
    sponsNym = sponsorSigner.verstr
    iNym = issuerSigner.verstr
    pNym = proverSigner.verstr
    vNym = verifierSigner.verstr

    for nym, ha in ((iNym, issuerHA), (pNym, proverHA), (vNym, verifierHA)):
        addNym(ha, looper, nym, sponsNym, sponsor)


@pytest.fixture(scope="module")
def attrNames():
    return "first_name", "last_name", "birth_date", "expire_date", \
           "undergrad", "postgrad"


@pytest.fixture(scope="module")
def credDef(attrNames):
    ip, port = genHa()
    return CredentialDefinition(attrNames, 'name1', 'version1',
                                p_prime=P_PRIME1, q_prime=Q_PRIME1,
                                ip=ip, port=port)


@pytest.fixture(scope="module")
def credentialDefinitionAdded(genned, updatedSteward, addedSponsor, sponsor,
                              sponsorSigner, looper, tdir, nodeSet, credDef):
    data = credDef.get(serFmt=SerFmt.base58)

    op = {
        TXN_TYPE: CRED_DEF,
        DATA: data
    }
    return submitAndCheck(looper, sponsor, op,
                          identifier=sponsorSigner.verstr)
