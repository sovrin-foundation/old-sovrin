import json
import os

import pytest
from sovrin.common.plugin_helper import writeAnonCredPlugin

from anoncreds.protocol.types import SerFmt
from anoncreds.protocol.utils import encodeAttrs

from plenum.client.signer import SimpleSigner

from plenum.test.helper import genHa
from anoncreds.protocol.credential_definition import CredentialDefinition
from anoncreds.temp_primes import P_PRIME1, Q_PRIME1
from sovrin.common.util import getConfig
from sovrin.test.helper import addNym

from plenum.common.txn import TXN_TYPE, DATA

from sovrin.common.txn import CRED_DEF
from sovrin.test.helper import submitAndCheck


# TODO Make a fixture for creating a client with a anon-creds features
#  enabled.

config = getConfig()


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


@pytest.fixture(scope="module")
def anonCredPluginFilePath(tdir):
    return os.path.expanduser(os.path.join(tdir, config.PluginsDir))


@pytest.fixture(scope="module", autouse=True)
def anonCredPluginFileCreated(tdir):
    # pluginsPath = anonCredPluginFilePath
    #
    # if not os.path.exists(pluginsPath):
    #     os.makedirs(pluginsPath)
    #
    # initFile = pluginsPath + "/__init__.py"
    # with open(initFile, "a"):
    #     pass
    #
    # anonPluginFilePath = pluginsPath + "/anoncreds.py"
    # anonPluginContent = "" \
    #                  "import importlib\n" \
    #                  "import anoncreds.protocol.issuer\n" \
    #                  "import sovrin.anon_creds.issuer\n" \
    #                  "from sovrin.client.client import Client\n" \
    #                  "\n" \
    #                  "Name = \"Anon creds\"\n" \
    #                  "Version = 1.1\n" \
    #                  "SovrinVersion = 2.1\n" \
    #                  "\n" \
    #                  "sovrin.anon_creds.issuer.Issuer = anoncreds.protocol.issuer.Issuer\n" \
    #                  "importlib.reload(sovrin.client.client)\n" \
    #                  "importlib.reload(sovrin.test.helper)\n"
    #     # "newMro = Client.__mro__[:4] + (sovrin.anon_creds.issuer.Issuer,) + Client.__mro__[5:]\n" \
    #                  # "sovrin.client.client.Client = type(Client.__name__, tuple(newMro), dict(Client.__dict__))"
    #
    # with open(anonPluginFilePath, "a") as myfile:
    #     myfile.write(anonPluginContent)
    #
    # assert os.path.exists(anonCredPluginFilePath)
    writeAnonCredPlugin(tdir)
