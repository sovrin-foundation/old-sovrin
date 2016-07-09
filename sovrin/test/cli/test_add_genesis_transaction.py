def testAddGenesisTransactions(cli):
    cli.parse("add genesis transactions xyz")
    assert 'Invalid command' not in cli.printeds
    assert "\ngenesis transactions set\n" in cli.printeds


def testSovrinStartupCreatesWalletAndKey(cli):
    assert "\nCurrent wallet set to Default\n" in cli.printeds
    assert "\nCurrent identifier set to" in cli.printeds
