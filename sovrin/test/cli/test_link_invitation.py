import pytest


def getLinkInvitation(name, cli):
    existingLinkInvites = cli.activeWallet.getMatchingLinkInvitations(name)
    li = existingLinkInvites[0]
    return li


@pytest.fixture(scope="module")
def loadedFaberLinkInvitation(cli):
    inviterName = "Faber College"
    cli.enterCmd("load sample/faber-invitation.sovrin")
    assert "1 link invitation found for {}.".format(inviterName) in cli.lastCmdOutput
    assert "Creating Link for {}.".format(inviterName) in cli.lastCmdOutput
    assert "Generating Identifier and Signing key." in cli.lastCmdOutput
    assert "Usage" in cli.lastCmdOutput
    assert "accept invitation {}".format(inviterName) in cli.lastCmdOutput
    assert "show link {}".format(inviterName) in cli.lastCmdOutput
    return cli

@pytest.fixture(scope="module")
def loadedAcmeCorpLinkInvitation(cli):
    employeeName = "Acme Corp"
    cli.enterCmd("load sample/acme-job-application.sovrin")
    assert "1 link invitation found for {}.".format(employeeName) in cli.lastCmdOutput
    assert "Creating Link for {}.".format(employeeName) in cli.lastCmdOutput
    assert "Generating Identifier and Signing key." in cli.lastCmdOutput
    assert "Usage" in cli.lastCmdOutput
    assert "accept invitation {}".format(employeeName) in cli.lastCmdOutput
    assert "show link {}".format(employeeName) in cli.lastCmdOutput
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


def testLoadFile(loadedAcmeCorpLinkInvitation):
    pass


def testShowLinkNotExists(cli):
    cli.enterCmd("show link Not Exists")
    assert "No matching link invitation(s) found in current keyring" in cli.lastCmdOutput


def testShowFaberLink(loadedFaberLinkInvitation):
    cli = loadedFaberLinkInvitation
    inviterName = "Faber College"
    cli.enterCmd("show link {}".format(inviterName))
    assert "Name: {}".format(inviterName) in cli.lastCmdOutput
    assert "Last synced: <this link has not yet been synchronized>" in cli.lastCmdOutput
    assert "Usage" in cli.lastCmdOutput
    assert "accept invitation {}".format(inviterName) in cli.lastCmdOutput
    assert "sync {}".format(inviterName) in cli.lastCmdOutput


def testShowAcmeCorpLink(loadedAcmeCorpLinkInvitation):
    cli = loadedAcmeCorpLinkInvitation
    employeeName = "Acme Corp"
    cli.enterCmd("show link {}".format(employeeName))
    assert "Name: {}".format(employeeName) in cli.lastCmdOutput
    assert "Claim Requests: " in cli.lastCmdOutput
    assert "Job Application" in cli.lastCmdOutput
    assert "Last synced: <this link has not yet been synchronized>" in cli.lastCmdOutput
    assert "Usage" in cli.lastCmdOutput
    assert "accept invitation {}".format(employeeName) in cli.lastCmdOutput
    assert "sync {}".format(employeeName) in cli.lastCmdOutput
