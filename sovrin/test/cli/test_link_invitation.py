import pytest


def getLinkInvitation(name, cli):
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
        assert "1 link invitation found for {}.".format(inviterName) in cli.lastCmdOutput
        assert "Creating Link for {}.".format(inviterName) in cli.lastCmdOutput
        assert "Generating Identifier and Signing key." in cli.lastCmdOutput

    assert "Usage" in cli.lastCmdOutput
    assert 'accept invitation "{}"'.format(inviterName) in cli.lastCmdOutput
    assert 'show link "{}"'.format(inviterName) in cli.lastCmdOutput


@pytest.fixture(scope="module")
def loadedFaberLinkInvitation(cli):
    loadFaberLinkInvitation(cli)
    return cli


def loadAcmeCorpLinkInvitation(cli):
    employeeName = "Acme Corp"
    cli.enterCmd("load sample/acme-job-application.sovrin")
    assert "1 link invitation found for {}.".format(employeeName) in cli.lastCmdOutput
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
    cli.enterCmd("load sample/faber-invitation.sovrin.not.exists")
    assert "Given file does not exists" in cli.lastCmdOutput


def testLoadFile(loadedFaberLinkInvitation):
    pass


def testLoadExistingLink(cli):
    loadFaberLinkInvitation(cli)
    loadFaberLinkInvitationAgain(cli)


def testLoadFile(loadedAcmeCorpLinkInvitation):
    pass


def testShowLinkNotExists(cli):
    cli.enterCmd("show link Not Exists")
    assert "No matching link invitation(s) found in current keyring" in cli.lastCmdOutput


def assertSowLinkOutput(cli, linkName):
    assert "Name: {}".format(linkName) in cli.lastCmdOutput
    assert "Last synced: <this link has not yet been synchronized>" in cli.lastCmdOutput
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
