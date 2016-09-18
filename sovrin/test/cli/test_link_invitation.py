import pytest
from plenum.client.signer import SimpleSigner
from plenum.common.txn import TARGET_NYM, TXN_TYPE, ROLE, NYM, RAW
from plenum.test.eventually import eventually
from sovrin.client.link_invitation import LinkInvitation
from sovrin.common.txn import USER, ATTRIB, ENDPOINT
from sovrin.test.cli.helper import ensureConnectedToTestEnv, \
    ensureNodesCreated, newCLI
from sovrin.test.helper import genTestClient
from plenum.test.conftest import poolTxnStewardData, poolTxnStewardNames


def getLinkInvitation(name, cli) -> LinkInvitation:
    existingLinkInvites = cli.activeWallet.getMatchingLinkInvitations(name)
    li = existingLinkInvites[0]
    return li


def loadFaberLinkInvitationAgain(cli):
    cli.enterCmd("load sample/faber-invitation.sovrin")
    assert "Link already exists" in cli.lastCmdOutput


def loadFaberLinkInvitation(cli, okIfAlreadyExists=False):
    inviterName = "Faber College"
    cli.enterCmd("load sample/faber-invitation.sovrin")
    checkNewLoadAsserts = True
    if okIfAlreadyExists and "Link already exists" in cli.lastCmdOutput:
        checkNewLoadAsserts = False

    if checkNewLoadAsserts:
        assert "1 link invitation found for {}.".format(inviterName) \
               in cli.lastCmdOutput
        assert "Creating Link for {}.".format(inviterName) in cli.lastCmdOutput
        assert "Generating Identifier and Signing key." in cli.lastCmdOutput

    assert "Usage" in cli.lastCmdOutput
    assert 'accept invitation "{}"'.format(inviterName) in cli.lastCmdOutput
    assert 'show link "{}"'.format(inviterName) in cli.lastCmdOutput


@pytest.fixture(scope="module")
def aliceCli(looper, tdir, tconf, tdirWithPoolTxns, tdirWithDomainTxns):
    cli = newCLI(looper, tdir, subDirectory="alice", conf=tconf,
                 poolDir=tdirWithPoolTxns, domainDir=tdirWithDomainTxns)
    return cli


@pytest.fixture(scope="module")
def loadedFaberLinkInvitation(aliceCli):
    loadFaberLinkInvitation(aliceCli)
    return aliceCli


def loadAcmeCorpLinkInvitation(cli):
    employeeName = "Acme Corp"
    cli.enterCmd("load sample/acme-job-application.sovrin")
    assert "1 link invitation found for {}.".format(employeeName) \
           in cli.lastCmdOutput
    assert "Creating Link for {}.".format(employeeName) in cli.lastCmdOutput
    assert "Generating Identifier and Signing key." in cli.lastCmdOutput
    assert "Usage" in cli.lastCmdOutput
    assert 'accept invitation "{}"'.format(employeeName) in cli.lastCmdOutput
    assert 'show link "{}"'.format(employeeName) in cli.lastCmdOutput


@pytest.fixture(scope="module")
def loadedAcmeCorpLinkInvitation(cli):
    loadAcmeCorpLinkInvitation(cli)
    return cli


def testShowFileNotExists(cli):
    cli.enterCmd("show {}".format("sample/faber-invitation.sovrin.not.exists"))
    assert "Given file does not exists" in cli.lastCmdOutput


def testShowFile(cli):
    cli.enterCmd("show {}".format("sample/faber-invitation.sovrin"))
    assert "Given file does not exists" not in cli.lastCmdOutput
    assert "link-invitation" in cli.lastCmdOutput


def testLoadFileNotExists(cli):
    cli.enterCmd("load sample/not-exists-file")
    assert "Given file does not exists" in cli.lastCmdOutput


def testLoadFile(loadedFaberLinkInvitation):
    pass


def testLoadExistingLink(cli):
    loadFaberLinkInvitation(cli)
    loadFaberLinkInvitationAgain(cli)


def testShowLinkNotExists(cli):
    cli.enterCmd("show link not-exists-link")
    assert "No matching link invitation(s) found in current keyring" \
           in cli.lastCmdOutput


def assertSowLinkOutput(cli, linkName):
    assert "Name: {}".format(linkName) in cli.lastCmdOutput
    assert "Last synced: <this link has not yet been synchronized>" \
           in cli.lastCmdOutput
    assert "Usage" in cli.lastCmdOutput
    assert 'accept invitation "{}"'.format(linkName) in cli.lastCmdOutput
    assert 'sync "{}"'.format(linkName) in cli.lastCmdOutput


def testShowFaberLink(cli):
    loadFaberLinkInvitation(cli, okIfAlreadyExists=True)
    inviterName = "Faber College"
    cli.enterCmd("show link {}".format(inviterName))
    assertSowLinkOutput(cli, inviterName)


def testShowAcmeCorpLink(loadedAcmeCorpLinkInvitation):
    cli = loadedAcmeCorpLinkInvitation
    employeeName = 'Acme Corp'
    cli.enterCmd('show link "{}"'.format(employeeName))
    assertSowLinkOutput(cli, employeeName)
    assert "Claim Requests: " in cli.lastCmdOutput
    assert "Job Application" in cli.lastCmdOutput


@pytest.fixture(scope="module")
def stewardClient(looper, tdirWithDomainTxns, poolTxnStewardData):
    name, seed = poolTxnStewardData
    signer = SimpleSigner(seed=seed)
    stewardClient = genTestClient(signer=signer, tmpdir=tdirWithDomainTxns,
                                  usePoolLedger=True)
    looper.add(stewardClient)
    looper.run(stewardClient.ensureConnectedToNodes())
    return stewardClient


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


def testSyncLinkNotExists(cli):
    cli.enterCmd("sync not-exists-link")
    assert "No matching link invitation(s) found in current keyring" \
           in cli.lastCmdOutput

def testSyncLinkWhenEndpointNotAvailable(looper, poolNodesCreated,
                                                   loadedFaberLinkInvitation,
                                                   stewardClient):
    aliceCli = loadedFaberLinkInvitation
    ensureConnectedToTestEnv(aliceCli)
    addNym(stewardClient, aliceCli.activeSigner.verstr)
    li = getLinkInvitation("Faber", aliceCli)
    addFaber(looper, stewardClient, li.targetIdentifier)

    aliceCli.enterCmd("sync Faber")
    looper.run(eventually(checkIfEndpointReceived, aliceCli, li.name,
                          "Endpoint not available",
                          retryWait=1,
                          timeout=10))


def testSyncLinkWhenEndpointIsAvailable(looper, poolNodesCreated,
                                                   loadedFaberLinkInvitation,
                                                   stewardClient):
    aliceCli = loadedFaberLinkInvitation
    ensureConnectedToTestEnv(aliceCli)
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