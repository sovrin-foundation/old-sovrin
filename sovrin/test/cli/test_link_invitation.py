import json

import pytest

from plenum.test.eventually import eventually
from plenum.test.pool_transactions.helper import buildPoolClientAndWallet
from sovrin.client.wallet.attribute import Attribute
from sovrin.client.wallet.attribute import LedgerStore
from sovrin.client.wallet.link_invitation import LinkInvitation
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.txn import USER, ATTRIB, ENDPOINT, SPONSOR
from sovrin.test.cli.helper import ensureConnectedToTestEnv
from sovrin.test.cli.conftest import getLinkInvitation
from sovrin.test.helper import genTestClient, makeNymRequest, makeAttribRequest, \
    makePendingTxnsRequest, createNym, TestClient

# noinspection PyUnresolvedReferences
from plenum.test.conftest import poolTxnStewardData, poolTxnStewardNames
from sovrin.test.test_client import addAttributeAndCheck


@pytest.fixture(scope="module")
def stewardClientAndWallet(poolNodesCreated, looper, tdirWithDomainTxns,
                           poolTxnStewardData):
    client, wallet = buildPoolClientAndWallet(poolTxnStewardData,
                                              tdirWithDomainTxns,
                                              clientClass=TestClient,
                                              walletClass=Wallet)
    client.registerObserver(wallet.handleIncomingReply)

    looper.add(client)
    looper.run(client.ensureConnectedToNodes())
    makePendingTxnsRequest(client, wallet)
    return client, wallet


@pytest.fixture(scope="module")
def aliceConnected(aliceCLI, be, do, poolNodesCreated):

    # Done to initialise a wallet.
    # TODO: a wallet should not be required for connecting, right?
    be(aliceCLI)
    do("new key")

    ensureConnectedToTestEnv(aliceCLI)
    return aliceCLI


def addNym(client, wallet, nym, role=USER):
    return makeNymRequest(client, wallet, nym, role)


def addFabersEndpoint(looper, client, wallet, nym, attrName, attrValue):
    val = json.dumps({attrName: attrValue})
    attrib = Attribute(name=attrName,
                       origin=wallet.defaultId,
                       value=val,
                       dest=nym,
                       ledgerStore=LedgerStore.RAW)
    addAttributeAndCheck(looper, client, wallet, attrib)


def checkIfEndpointReceived(aCli, linkName, expStr):
    assert expStr in aCli.lastCmdOutput
    assert "Usage" in aCli.lastCmdOutput
    assert 'show link "{}"'.format(linkName) in aCli.lastCmdOutput
    assert 'accept invitation "{}"'.format(linkName) in aCli.lastCmdOutput
    if "Endpoint received" in expStr:
        li = getLinkInvitation("Faber", aCli)
        assert li.targetEndPoint is not None


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


@pytest.fixture(scope="module")
def faberAdded(poolNodesCreated,
             looper,
             aliceCLI,
             faberInviteLoaded,
             aliceConnected,
             stewardClientAndWallet):
    client, wallet = stewardClientAndWallet
    li = getLinkInvitation("Faber", aliceCLI)
    createNym(looper, li.targetIdentifier, client, wallet, role=SPONSOR)


def testSyncLinkWhenEndpointNotAvailable(faberAdded,
                                         looper,
                                         aliceCLI,
                                         stewardClientAndWallet):
    li = getLinkInvitation("Faber", aliceCLI)
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
    li = getLinkInvitation("Faber", aliceCLI)
    assert li.targetEndPoint is None
    endpointValue = "0.0.0.0:0000"
    addFabersEndpoint(looper, client, wallet, li.targetIdentifier,
                      ENDPOINT, endpointValue)
    aliceCLI.enterCmd("sync Faber")
    looper.run(eventually(checkIfEndpointReceived, aliceCLI, li.name,
                          "Endpoint received: {}".format(endpointValue),
                          retryWait=1,
                          timeout=10))
