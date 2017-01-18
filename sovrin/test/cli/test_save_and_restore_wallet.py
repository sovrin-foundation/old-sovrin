import os
from os.path import basename
from time import sleep

import pytest
from plenum.cli.cli import Exit, Cli
from sovrin.test.cli.helper import prompt_is


def performExit(do):
    with pytest.raises(Exit):
        do('exit', within=3)


def testPersistentWalletName():
    cliName = "sovrin"

    # Connects to "test" environment
    walletFileName = Cli.getPersistentWalletFileName(
        cliName=cliName, currPromptText="sovrin@test")
    assert "keyring_test" == walletFileName
    assert "test" == Cli.getWalletKeyName(walletFileName)

    # New default wallet (keyring) gets created
    walletFileName = Cli.getPersistentWalletFileName(
        cliName=cliName, currPromptText="sovrin@test",
        walletName="Default")
    assert "keyring_default_test" == walletFileName
    assert "default" == Cli.getWalletKeyName(walletFileName)

    # User creates new wallet (keyring)
    walletFileName = Cli.getPersistentWalletFileName(
        cliName=cliName, currPromptText="sovrin@test",
        walletName="MyVault")
    assert "keyring_myvault_test" == walletFileName
    assert "myvault" == Cli.getWalletKeyName(walletFileName)


def checkWalletFilePersisted(filePath):
    assert os.path.exists(filePath)


def checkWalletRestored(expectedWalletKeyName, cli,
                       expectedIdentifiers):

    cli.lastCmdOutput == "Saved keyring {} restored".format(
        expectedWalletKeyName)
    assert cli._activeWallet.name == expectedWalletKeyName
    assert len(cli._activeWallet.identifiers) == \
           expectedIdentifiers


def getWalletFilePath(cli):
    activeWalletName = cli._activeWallet.name if cli._activeWallet else ""
    fileName = Cli.getPersistentWalletFileName(
        cli.name, cli.currPromptText, activeWalletName)
    return Cli.getWalletFilePath(cli.getKeyringsBaseDir(), fileName)


def getOldIdentifiersForActiveWallet(cli):
    oldIdentifiers = 0
    if cli._activeWallet:
        oldIdentifiers = len(cli._activeWallet.identifiers)
    return oldIdentifiers


def createNewKey(do, cli, keyringName):
    oldIdentifiers = getOldIdentifiersForActiveWallet(cli)
    do('new key', within=2,
       expect=["Key created in keyring {}".format(keyringName)])
    assert len(cli._activeWallet.identifiers) == oldIdentifiers + 1


def createNewKeyring(name, do, expectedMsgs=None):
    finalExpectedMsgs = expectedMsgs if expectedMsgs else [
           'Active keyring set to "{}"'.format(name),
           'New keyring {} created'.format(name)
        ]
    do(
        'new keyring {}'.format(name),
        expect=finalExpectedMsgs
    )


def useKeyring(name, do, expectedName=None, expectedMsgs=None):
    keyringName = expectedName or name
    finalExpectedMsgs = expectedMsgs or \
                        ['Active keyring set to "{}"'.format(keyringName)]
    do('use keyring {}'.format(name),
       expect=finalExpectedMsgs
    )


def _connectTo(envName, do, cli):
    do('connect {}'.format(envName), within=10,
       expect=["Connected to {}".format(envName)])
    prompt_is("{}@{}".format(cli.name, envName))


def connectTo(envName, do, cli, activeWalletPresents, identifiers,
              firstTimeConnect=False):
    currActiveWallet = cli._activeWallet
    _connectTo(envName, do, cli)
    if currActiveWallet is None and firstTimeConnect:
        do(None, expect=[
            "New keyring Default created",
            'Active keyring set to "Default"']
        )

    if activeWalletPresents:
        assert cli._activeWallet is not None
        assert len(cli._activeWallet.identifiers) == identifiers
    else:
        assert cli._activeWallet is None


def switchEnv(newEnvName, do, cli, checkIfWalletRestored=False,
              restoredWalletKeyName=None, restoredIdentifiers=0):
    walletFilePath = getWalletFilePath(cli)
    _connectTo(newEnvName, do, cli)
    # check wallet should have been persisted

    checkWalletFilePersisted(walletFilePath)
    if checkIfWalletRestored:
        checkWalletRestored(restoredWalletKeyName, cli, restoredIdentifiers)


def exit(do):
    with pytest.raises(Exit):
        do('exit', expect='Goodbye.')


def restartCli(CliBuilder, be, do, expectedRestoredWalletName,
               expectedIdentifiers):
    cli = yield from CliBuilder("alice")
    be(cli)
    do(None, expect=[
        'Running Sovrin',
        'Saved keyring "{}" restored'.format(expectedRestoredWalletName),
        'Active keyring set to "{}"'.format(expectedRestoredWalletName)
    ], within=5)
    assert cli._activeWallet is not None
    assert len(cli._activeWallet.identifiers) == expectedIdentifiers


def testSaveAndRestoreWallet(do, be, cliForMultiNodePools, CliBuilder):
    be(cliForMultiNodePools)
    # No wallet should have been restored
    assert cliForMultiNodePools._activeWallet is None

    connectTo("pool1", do, cliForMultiNodePools,
              activeWalletPresents=True, identifiers=0, firstTimeConnect=True)
    createNewKey(do, cliForMultiNodePools, keyringName="Default")

    switchEnv("pool2", do, cliForMultiNodePools, checkIfWalletRestored=False)
    createNewKey(do, cliForMultiNodePools, keyringName="Default")
    createNewKeyring("mykr0", do)
    createNewKey(do, cliForMultiNodePools, keyringName="mykr0")
    createNewKey(do, cliForMultiNodePools, keyringName="mykr0")
    useKeyring("Default", do)
    createNewKey(do, cliForMultiNodePools, keyringName="Default")
    sleep(20)
    switchEnv("pool1", do, cliForMultiNodePools, checkIfWalletRestored=True,
              restoredWalletKeyName="Default", restoredIdentifiers=1)
    createNewKeyring("mykr1", do)
    createNewKey(do, cliForMultiNodePools, keyringName="mykr1")

    switchEnv("pool2", do, cliForMultiNodePools, checkIfWalletRestored=True,
              restoredWalletKeyName="Default", restoredIdentifiers=2)
    createNewKeyring("mykr0", do,
                     expectedMsgs = [
                         "mykr0 conflicts with an existing keyring name",
                         "Please choose a new name"])

    filePath = Cli.getWalletFilePath(cliForMultiNodePools.getKeyringsBaseDir(),
                                     cliForMultiNodePools.walletFileName)
    switchEnv("pool1", do, cliForMultiNodePools, checkIfWalletRestored=True,
              restoredWalletKeyName="mykr1", restoredIdentifiers=1)
    useKeyring(filePath, do, expectedName="mykr0",
               expectedMsgs=['Saved keyring "Default" restored'])
    exit(do)

    restartCli(CliBuilder, be, do, "Default", 1)