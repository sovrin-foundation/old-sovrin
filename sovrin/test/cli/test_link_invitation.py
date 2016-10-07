import pytest
from plenum.test.eventually import eventually
from sovrin.cli.helper import NEXT_COMMANDS_TO_TRY_TEXT

from sovrin.client.wallet.link import constant
from sovrin.common.txn import USER, ENDPOINT
from sovrin.test.cli.helper import ensureConnectedToTestEnv, getLinkInvitation
from sovrin.test.helper import addRawAttribute


@pytest.fixture(scope="module")
def aliceConnected(aliceCLI, be, do, poolNodesCreated):
    # Done to initialise a wallet.
    be(aliceCLI)
    do("new key")

    ensureConnectedToTestEnv(aliceCLI)
    return aliceCLI


def checkIfEndpointReceived(aCli, linkName, expStr):
    assert NEXT_COMMANDS_TO_TRY_TEXT in aCli.lastCmdOutput
    assert 'show link "{}"'.format(linkName) in aCli.lastCmdOutput
    assert 'accept invitation from "{}"'.format(linkName) in aCli.lastCmdOutput
    if "Endpoint received" in expStr:
        li = getLinkInvitation("Faber", aCli.activeWallet)
        assert li.remoteEndPoint is not None


def testShowFileNotExists(aliceCLI, be, do, fileNotExists, faberMap):
    be(aliceCLI)
    do("show {invite-not-exists}", expect=fileNotExists, mapper=faberMap)


def testShowFile(aliceCLI, be, do, faberMap):
    be(aliceCLI)
    do("show {invite}", expect="link-invitation",
                        not_expect="Given file does not exist",
                        mapper=faberMap)


def testLoadFileNotExists(aliceCLI, be, do, fileNotExists, faberMap):
    be(aliceCLI)
    do("load {invite-not-exists}", expect=fileNotExists, mapper=faberMap)


def testLoadFile(faberInviteLoaded):
    pass


def testLoadSecondFile(faberInviteLoaded, acmeInviteLoaded):
    pass


def testLoadExistingLink(aliceCLI, be, do, faberInviteLoaded,
                         linkAlreadyExists, faberMap):
    be(aliceCLI)
    do("load {invite}", expect=linkAlreadyExists, mapper=faberMap)


def testShowLinkNotExists(aliceCLI, be, do, linkNotExists, faberMap):
    be(aliceCLI)
    do("show link {inviter-not-exists}", expect=linkNotExists, mapper=faberMap)


def testShowFaberLink(aliceCLI, faberInviteLoaded, be, do, faberMap, showLinkOut):
    be(aliceCLI)
    do("show link {inviter}", expect=showLinkOut, mapper=faberMap)


def testShowAcmeLink(aliceCLI, acmeInviteLoaded, be, do, acmeMap, showLinkOut):
    be(aliceCLI)
    expected = showLinkOut + ["Claim Requests: {claim-requests}"]
    do("show link {inviter}", expect=expected, mapper=acmeMap)


def testSyncLinkNotExists(aliceCLI, be, do, linkNotExists, faberMap):
    be(aliceCLI)
    do("sync {inviter-not-exists}", expect=linkNotExists, mapper=faberMap)


def testAliceConnect(aliceConnected):
    pass


def testSyncLinkWhenEndpointNotAvailable(faberAdded,
                                         looper,
                                         aliceCLI,
                                         stewardClientAndWallet):
    li = getLinkInvitation("Faber", aliceCLI.activeWallet)
    aliceCLI.enterCmd("sync Faber")
    looper.run(eventually(checkIfEndpointReceived, aliceCLI, li.name,
                          "Endpoint not available",
                          retryWait=1,
                          timeout=10))


def testSyncLinkWhenEndpointIsAvailable(looper,
                                        aliceCLI,
                                        stewardClientAndWallet,
                                        faberAdded):
    client, wallet = stewardClientAndWallet
    li = getLinkInvitation("Faber", aliceCLI.activeWallet)
    assert li.remoteEndPoint is constant.NOT_AVAILABLE
    endpointValue = "0.0.0.0:0000"
    addRawAttribute(looper, client, wallet, ENDPOINT, endpointValue,
                    dest=li.remoteIdentifier)
    aliceCLI.enterCmd("sync Faber")
    looper.run(eventually(checkIfEndpointReceived, aliceCLI, li.name,
                          "Endpoint received: {}".format(endpointValue),
                          retryWait=1,
                          timeout=10))

