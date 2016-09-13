def testShowFile(cli):
    cli.enterCmd("show {}".format("sample/faber-invitation.sovrin"))
    assert "Given file does not exists" not in cli.lastCmdOutput
    assert "link-invitation" in cli.lastCmdOutput
