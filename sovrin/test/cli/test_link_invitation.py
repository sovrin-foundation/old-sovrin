def testShowFile(cli):
    cli.enterCmd("show {}".format("sample/faber-invitation.sovrin"))
    assert "Given file does not exists" not in cli.lastCmdOutput
    assert "link-invitation" in cli.lastCmdOutput


def testShowFileNotExists(cli):
    cli.enterCmd("show {}".format("sample/faber-invitation.sovrin.not.exists"))
    assert "Given file does not exists" in cli.lastCmdOutput


def testLoadFile(cli):
    collegeName = "Faber College"
    cli.enterCmd("load sample/faber-invitation.sovrin")
    assert "1 link invitation found for {}.".format(collegeName) in cli.lastCmdOutput
    assert "Creating Link for {}.".format(collegeName) in cli.lastCmdOutput
    assert "Generating Identifier and Signing key." in cli.lastCmdOutput


def testLoadFileNotExists(cli):
    cli.enterCmd("load sample/faber-invitation.sovrin.not.exists")
    assert "Given file does not exists" in cli.lastCmdOutput


def testShowLink(cli):
    collegeName = "Acme Corp"
    cli.enterCmd("load sample/acme-job-application.sovrin")
    assert "1 link invitation found for {}.".format(collegeName) in cli.lastCmdOutput
    assert "Creating Link for {}.".format(collegeName) in cli.lastCmdOutput
    assert "Generating Identifier and Signing key." in cli.lastCmdOutput
    existingLinkInvites = cli.activeWallet.getLinkInvitations(collegeName)
    li = existingLinkInvites[0]
    cli.enterCmd("show link Acme Corp")
    linkInfo = li.getLinkInfo()
    # TODO: Need to add some asserts for show link command output


