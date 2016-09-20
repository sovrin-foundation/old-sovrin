import pytest
from plenum.client.signer import SimpleSigner
from plenum.common.txn import TARGET_NYM, TXN_TYPE, ROLE, NYM, RAW
from plenum.test.eventually import eventually
from sovrin.client.link_invitation import LinkInvitation
from sovrin.common.txn import USER, ATTRIB, ENDPOINT
from sovrin.test.cli.helper import ensureConnectedToTestEnv
from sovrin.test.helper import genTestClient

# noinspection PyUnresolvedReferences
from plenum.test.conftest import poolTxnStewardData, poolTxnStewardNames


def getLinkInvitation(name, cli) -> LinkInvitation:
    existingLinkInvites = cli.activeWallet.getMatchingLinkInvitations(name)
    li = existingLinkInvites[0]
    return li


@pytest.yield_fixture(scope="module")
def aliceCli(CliBuilder):
    yield from CliBuilder("alice")


@pytest.fixture(scope="module")
def faberMap():
    return {'inviter': 'Faber College',
            'invite': "sample/faber-invitation.sovrin",
            'invite-not-exists': "sample/faber-invitation.sovrin.not.exists",
            'inviter-not-exists': "non-existing-inviter"
            }


@pytest.fixture(scope="module")
def loadInviteOut():
    return ["1 link invitation found for {inviter}.",
            "Creating Link for {inviter}.",
            "Generating Identifier and Signing key.",
            "Usage",
            'accept invitation "{inviter}"',
            'show link "{inviter}"']


@pytest.fixture(scope="module")
def loadInviteNotFoundOut():
    return ["Given file does not exist"]


@pytest.fixture(scope="module")
def linkAlreadyExists():
    return ["Link already exists"]


@pytest.fixture(scope="module")
def linkNotExists():
    return ["No matching link invitation(s) found in current keyring"]


@pytest.fixture(scope="module")
def faberInviteLoaded(aliceCli, be, do, faberMap, loadInviteOut):
    be(aliceCli)
    do("load {invite}", expect=loadInviteOut, mapper=faberMap)


@pytest.fixture(scope="module")
def acmeMap():
    return {'inviter': 'Acme Corp',
            'invite': "sample/acme-job-application.sovrin"}


@pytest.fixture(scope="module")
def acmeInviteLoaded(aliceCli, be, do, acmeMap, loadInviteOut):
    be(aliceCli)
    do("load {invite}", expect=loadInviteOut, mapper=acmeMap)


@pytest.fixture(scope="module")
def showLinkOut():
    return ["Name: {inviter}",
            "Last synced: <this link has not yet been synchronized>",
            "Usage",
            'accept invitation "{inviter}"',
            'sync "{inviter}"']


@pytest.fixture(scope="module")
def stewardClient(looper, tdirWithDomainTxns, poolTxnStewardData):
    name, seed = poolTxnStewardData
    signer = SimpleSigner(seed=seed)
    stewardClient = genTestClient(signer=signer, tmpdir=tdirWithDomainTxns,
                                  usePoolLedger=True)
    looper.add(stewardClient)
    looper.run(stewardClient.ensureConnectedToNodes())
    return stewardClient


@pytest.fixture(scope="module")
def aliceConnected(aliceCli, be, do, poolNodesCreated):

    # Done to initialise a wallet.
    # TODO: a wallet should not be required for connecting, right?
    be(aliceCli)
    do("new key")

    ensureConnectedToTestEnv(aliceCli)
    return aliceCli


def addNym(stewardClient, nym):
    addNym = {
        TARGET_NYM: nym,
        TXN_TYPE: NYM,
        ROLE: USER
    }
    stewardClient.submit(addNym, identifier=stewardClient.defaultIdentifier)


def addFabersEndpoint(stewardClient, nym, attrName, attrValue):
    addEndpoint = {
        TARGET_NYM: nym,
        TXN_TYPE: ATTRIB,
        RAW: '{"' + attrName + '": "' + attrValue + '"}'
    }
    stewardClient.submit(addEndpoint, identifier=stewardClient.defaultIdentifier)


def addFaber(looper, stewardClient, aliceNym):
    addNym(stewardClient, aliceNym)


def checkIfEndpointReceived(aCli, linkName, expStr):
    assert expStr in aCli.lastCmdOutput
    assert "Usage" in aCli.lastCmdOutput
    assert 'show link "{}"'.format(linkName) in aCli.lastCmdOutput
    assert 'accept invitation "{}"'.format(linkName) in aCli.lastCmdOutput
    if "Endpoint received" in expStr:
        li = getLinkInvitation("Faber", aCli)
        assert li.targetEndPoint is not None


def testShowFileNotExists(aliceCli, be, do, loadInviteNotFoundOut, faberMap):
    be(aliceCli)
    do("show {invite-not-exists}", expect=loadInviteNotFoundOut, mapper=faberMap)


def testShowFile(aliceCli, be, do, faberMap):
    be(aliceCli)
    do("show {invite}", expect="link-invitation",
                        not_expect="Given file does not exist",
                        mapper=faberMap)


def testLoadFileNotExists(aliceCli, be, do, loadInviteNotFoundOut, faberMap):
    be(aliceCli)
    do("load {invite-not-exists}", expect=loadInviteNotFoundOut, mapper=faberMap)


def testLoadFile(faberInviteLoaded):
    pass


def testLoadSecondFile(faberInviteLoaded, acmeInviteLoaded):
    pass


def testLoadExistingLink(aliceCli, be, do, faberInviteLoaded,
                         linkAlreadyExists, faberMap):
    be(aliceCli)
    do("load {invite}", expect=linkAlreadyExists, mapper=faberMap)


def testShowLinkNotExists(aliceCli, be, do, linkNotExists, faberMap):
    be(aliceCli)
    do("show link {inviter-not-exists}", expect=linkNotExists, mapper=faberMap)


def testShowFaberLink(aliceCli, faberInviteLoaded, be, do, faberMap, showLinkOut):
    be(aliceCli)
    do("show link {inviter}", expect=showLinkOut, mapper=faberMap)


def testShowAcmeLink(aliceCli, acmeInviteLoaded, be, do, acmeMap, showLinkOut):
    be(aliceCli)
    expected = showLinkOut + ["Claim Requests: ",
                              "Job Application"]
    do("show link {inviter}", expect=expected, mapper=acmeMap)


def testSyncLinkNotExists(aliceCli, be, do, linkNotExists, faberMap):
    be(aliceCli)
    do("sync {inviter-not-exists}", expect=linkNotExists, mapper=faberMap)


def testAliceConnect(aliceConnected):
    pass


def testSyncLinkWhenEndpointNotAvailable(looper,
                                         aliceCli,
                                         poolNodesCreated,
                                         faberInviteLoaded,
                                         aliceConnected,
                                         stewardClient):
    addNym(stewardClient, aliceCli.activeSigner.verstr)
    li = getLinkInvitation("Faber", aliceCli)
    addFaber(looper, stewardClient, li.targetIdentifier)

    aliceCli.enterCmd("sync Faber")
    looper.run(eventually(checkIfEndpointReceived, aliceCli, li.name,
                          "Endpoint not available",
                          retryWait=1,
                          timeout=10))


def testSyncLinkWhenEndpointIsAvailable(looper,
                                        aliceCli,
                                        poolNodesCreated,
                                        faberInviteLoaded,
                                        aliceConnected,
                                        stewardClient):
    addNym(stewardClient, aliceCli.activeSigner.verstr)
    li = getLinkInvitation("Faber", aliceCli)
    assert li.targetEndPoint is None
    addFaber(looper, stewardClient, li.targetIdentifier)
    looper.runFor(0.5)

    endpointValue = "0.0.0.0:0000"
    addFabersEndpoint(stewardClient, li.targetIdentifier,
                      ENDPOINT, endpointValue)
    looper.runFor(0.5)
    aliceCli.enterCmd("sync Faber")
    looper.run(eventually(checkIfEndpointReceived, aliceCli, li.name,
                          "Endpoint received: {}".format(endpointValue),
                          retryWait=1,
                          timeout=10))
