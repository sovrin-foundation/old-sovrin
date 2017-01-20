import pytest
from plenum.common.signer_simple import SimpleSigner
from sovrin.client.wallet.wallet import Wallet
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


def getNym(be, do, userCli, idr, expectedMsgs):
    be(userCli)
    do('send GET_NYM dest={}'.format(idr),
       within=3,
       expect=["Transaction id for NYM {} is".format(idr)] + expectedMsgs
    )


def getNymNotFoundExpectedMsgs(idr):
    return ["NYM {} not found".format(idr)]


def testGetDIDNymWithoutAddingIt(be, do, philCli, abbrevIdr):
    getNym(be, do, philCli, abbrevIdr,
            getNymNotFoundExpectedMsgs(abbrevIdr))


def testGetCIDNymWithoutAddingIt(be, do, philCli, sponsorSigner):
    getNym(be, do, philCli, sponsorSigner.identifier,
            getNymNotFoundExpectedMsgs(sponsorSigner.identifier))


def addNym(be, do, userCli, idr, verkey=None):
    be(userCli)
    cmd='send NYM dest={} role=SPONSOR'.format(idr)
    if verkey is not None:
        cmd='{} verkey={}'.format(cmd, verkey)

    do(cmd, within=3, expect=["Nym {} added".format(idr)])


@pytest.fixture(scope="module")
def didNymAdded(be, do, philCli, abbrevIdr):
    addNym(be, do, philCli, abbrevIdr)
    return philCli


def testAddDIDNym(didNymAdded):
    pass


@pytest.fixture(scope="module")
def cidNymAdded(be, do, philCli, sponsorSigner):
    addNym(be, do, philCli, sponsorSigner.identifier)
    return philCli


def testAddCIDNym(cidNymAdded):
    pass


def getNoVerkeyEverAssignedMsgs(idr):
    return ["No verkey ever assigned to the identifier {}".format(idr)]


def testGetDIDNymWithoutVerkey(be, do, philCli, didNymAdded, abbrevIdr):
    getNym(be, do, philCli, abbrevIdr,
            getNoVerkeyEverAssignedMsgs(abbrevIdr))


def getVerkeyIsSameAsIdentifierMsgs(idr):
    return ["Current verkey is same as identifier {}".format(idr)]


def testGetCIDNymWithoutVerkey(be, do, philCli, cidNymAdded, sponsorSigner):
    getNym(be, do, philCli, sponsorSigner.identifier,
                         getVerkeyIsSameAsIdentifierMsgs(sponsorSigner.identifier))


@pytest.fixture(scope="module")
def verkeyAddedToDIDNym(be, do, philCli, didNymAdded,
                                  abbrevIdr, abbrevVerkey):
    addNym(be, do, philCli, abbrevIdr, abbrevVerkey)


def testAddVerkeyToExistingDIDNym(verkeyAddedToDIDNym):
    pass


@pytest.fixture(scope="module")
def verkeyAddedToCIDNym(be, do, philCli, cidNymAdded, sponsorSigner):
    newSigner = SimpleSigner()
    addNym(be, do, philCli, sponsorSigner.identifier, newSigner.identifier)
    return newSigner


def testAddVerkeyToExistingCIDNym(verkeyAddedToCIDNym):
    pass


def getCurrentVerkeyIsgMsgs(idr, verkey):
    return ["Current verkey for NYM {} is {}".format(idr, verkey)]


def testGetDIDNymWithVerKey(be, do, philCli, verkeyAddedToDIDNym,
                            abbrevIdr, abbrevVerkey):
    getNym(be, do, philCli, abbrevIdr,
           getCurrentVerkeyIsgMsgs(abbrevIdr, abbrevVerkey))


def testGetCIDNymWithVerKey(be, do, philCli, verkeyAddedToCIDNym,
                            sponsorSigner):
    getNym(be, do, philCli, sponsorSigner.identifier,
           getCurrentVerkeyIsgMsgs(sponsorSigner.identifier,
                                   verkeyAddedToCIDNym.identifier))


def getNoActiveVerkeyFoundMsgs(idr):
    return ["No active verkey found for the identifier {}".format(idr)]


@pytest.fixture(scope="module")
def verkeyRemovedFromExistingDIDNym(be, do, philCli, verkeyAddedToDIDNym,
                                 abbrevIdr):
    be(philCli)
    addNym(be, do, philCli, abbrevIdr, '')
    getNym(be, do, philCli, abbrevIdr, getNoActiveVerkeyFoundMsgs(abbrevIdr))


def testRemoveVerkeyFromDIDNym(verkeyRemovedFromExistingDIDNym):
    pass


@pytest.fixture(scope="module")
def verkeyRemovedFromExistingCIDNym(be, do, philCli, verkeyAddedToCIDNym,
                                 sponsorSigner):
    be(philCli)
    addNym(be, do, philCli, sponsorSigner.identifier, '')
    getNym(be, do, philCli, sponsorSigner.identifier,
           getNoActiveVerkeyFoundMsgs(sponsorSigner.identifier))


def testRemoveVerkeyFromCIDNym(verkeyRemovedFromExistingCIDNym):
    pass


def testNewVerkeyAddedToDIDNym(be, do, philCli, abbrevIdr,
                               verkeyRemovedFromExistingDIDNym):
    newSigner = SimpleSigner()
    addNym(be, do, philCli, abbrevIdr, newSigner.verkey)
    getNym(be, do, philCli, abbrevIdr,
           getCurrentVerkeyIsgMsgs(abbrevIdr, newSigner.verkey))


def testNewVerkeyAddedToCIDNym(be, do, philCli, sponsorSigner,
                               verkeyRemovedFromExistingCIDNym):
    newSigner = SimpleSigner()
    addNym(be, do, philCli, sponsorSigner.identifier, newSigner.verkey)
    getNym(be, do, philCli, sponsorSigner.identifier,
           getCurrentVerkeyIsgMsgs(sponsorSigner.identifier, newSigner.verkey))


def testNewKeyChangesWalletsDefaultId(be, do, poolNodesStarted,
                                      aliceCLI, connectedToTest):
    mywallet = Wallet('my wallet')
    keyseed='a'*32
    idr, _ = mywallet.addIdentifier(seed=keyseed.encode("utf-8"))

    be(aliceCLI)

    do('connect test', within=3, expect=connectedToTest)

    do('new key with seed {}'.format(keyseed))

    do('send NYM dest={}'.format(idr))

    do('new key with seed 11111111111111111111111111111111')

    do('send NYM dest={}'.format(idr),
       within=3,
       expect=["Nym {} added".format(idr)]
    )


def addAttribToNym(be, do, userCli, idr, raw):
    be(userCli)
    do('send ATTRIB dest={} raw={}'.format(idr, raw),
       within=3,
       expect=["Attribute added for nym {}".format(idr)])


def testSendAttribForDIDNym(be, do, philCli, didNymAdded, abbrevIdr):
    raw = '{"name": "Alice"}'
    addAttribToNym(be, do, philCli, abbrevIdr, raw)


def testSendAttribForCIDNym(be, do, philCli, cidNymAdded, sponsorSigner):
    raw = '{"name": "Alice"}'
    addAttribToNym(be, do, philCli, sponsorSigner.identifier, raw)
