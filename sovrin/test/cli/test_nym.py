import pytest
from plenum.common.signer_simple import SimpleSigner
from sovrin.test.cli.test_tutorial import prompt_is
from sovrin.test.did.conftest import wallet, abbrevVerkey, abbrevIdr


@pytest.fixture("module")
def sponsorSigner():
    return SimpleSigner()


@pytest.fixture(scope="module")
def poolNodesStarted(be, do, poolCLI):
    be(poolCLI)

    do('new node all', within=6,
       expect=['Alpha now connected to Beta',
               'Alpha now connected to Gamma',
               'Alpha now connected to Delta',
               'Beta now connected to Alpha',
               'Beta now connected to Gamma',
               'Beta now connected to Delta',
               'Gamma now connected to Alpha',
               'Gamma now connected to Beta',
               'Gamma now connected to Delta',
               'Delta now connected to Alpha',
               'Delta now connected to Beta',
               'Delta now connected to Gamma'])
    return poolCLI


def testPoolNodesStarted(poolNodesStarted):
    pass


@pytest.fixture(scope="module")
def philCli(be, do, poolNodesStarted, philCLI, connectedToTest):
    be(philCLI)
    do('prompt Phil', expect=prompt_is('Phil'))

    do('new keyring Phil', expect=['New keyring Phil created',
                                   'Active keyring set to "Phil"'])

    mapper = {
        'seed': '11111111111111111111111111111111',
        'idr': '5rArie7XKukPCaEwq5XGQJnM9Fc5aZE3M9HAPVfMU2xC'}
    do('new key with seed {seed}', expect=['Key created in keyring Phil',
                                           'Identifier for key is {idr}',
                                           'Current identifier set to {idr}'],
       mapper=mapper)

    do('connect test', within=3, expect=connectedToTest)
    return philCLI


@pytest.fixture(scope="module")
def nymAdded(be, do, philCli, abbrevIdr):
    be(philCli)

    do('send NYM dest={} role=SPONSOR'.format(abbrevIdr),
       within=3,
       expect=["Nym {} added".format(abbrevIdr)]
    )
    return philCli


def testAddNym(nymAdded):
    pass


@pytest.fixture(scope="module")
def nymRetrieved(be, do, philCli, nymAdded, abbrevIdr):
    be(philCli)

    do('send GET_NYM dest={}'.format(abbrevIdr),
       within=3,
       expect=["Transaction id for NYM {} is".format(abbrevIdr)]
    )


def testGetNym(nymRetrieved):
    pass


def testSendAttrib(be, do, philCli, nymRetrieved, abbrevIdr):
    raw = '{"name": "Alice"}'
    be(philCli)
    do('send ATTRIB dest={} raw={}'.format(abbrevIdr, raw),
        within=3,
       expect=["Attribute added for nym {}".format(abbrevIdr)])


@pytest.fixture(scope="module")
def verkeyAddedToExistingNym(be, do, philCli, nymAdded, abbrevIdr, abbrevVerkey):
    be(philCli)

    do('send NYM dest={} role=SPONSOR verkey={}'.format(
        abbrevIdr, abbrevVerkey),
       within=3,
       expect=["Nym {} added".format(abbrevIdr)]
    )
    return philCli


def testAddVerkeyToExistingNym(verkeyAddedToExistingNym):
    pass


@pytest.fixture(scope="module")
def nymRetrievedWithVerkey(be, do, philCli, verkeyAddedToExistingNym,
                           abbrevIdr, abbrevVerkey):
    be(philCli)

    do('send GET_NYM dest={}'.format(abbrevIdr),
       within=3,
       expect=[
           "Transaction id for NYM {} is".format(abbrevIdr),
           "Current verkey for NYM {} is {}".format(abbrevIdr, abbrevVerkey)
       ]
    )


def testGetNymWithVerkey(nymRetrievedWithVerkey):
    pass