def testAddGenesisTransactions(cli):
    cli.parse("add genesis transactions xyz")
    assert 'Invalid command' not in cli.printed
    assert "\ngenesis transactions set\n" in cli.printed


def testSovrinStartupCreatesWalletAndKey(cli):
    assert "\nCurrent wallet set to Default\n" in cli.printed
    assert "\nCurrent identifier set to" in cli.printed
