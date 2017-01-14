import os

import pytest
from plenum.cli.cli import Exit, Cli
from sovrin.test.cli.conftest import savedKeyringRestored
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
        activeWalletName="Default")
    assert "keyring_Default_test" == walletFileName
    assert "Default" == Cli.getWalletKeyName(walletFileName)

    # User creates new wallet (keyring)
    walletFileName = Cli.getPersistentWalletFileName(
        cliName=cliName, currPromptText="sovrin@test",
        activeWalletName="MyVault")
    assert "keyring_MyVault_test" == walletFileName
    assert "MyVault" == Cli.getWalletKeyName(walletFileName)


def checkWalletFilePersisted(filePath):
    assert os.path.exists(filePath)


def checkWalletRestored(expectedWalletKeyName, cliForMultiNodePools,
                       expectedIdentifiers):
    assert cliForMultiNodePools._activeWallet.name == expectedWalletKeyName
    assert len(cliForMultiNodePools._activeWallet.identifiers) == \
           expectedIdentifiers



def getWalletFilePath(cli):
    activeWalletName = cli._activeWallet.name if cli._activeWallet else ""
    fileName = Cli.getPersistentWalletFileName(
        cli.name, cli.currPromptText, activeWalletName)
    return Cli.getWalletFilePath(cli.config.baseDir, fileName)


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


def createNewKeyring(name, do):
    do (
        'new keyring {}'.format(name),
        expect=[
           'Active keyring set to "{}"'.format(name),
           'New keyring {} created'.format(name)
        ]
    )


def connectTo(envName, do, cli, activeWalletPresents, identifiers):
    do('connect {}'.format(envName), within=5,
       expect=["Connected to {}".format(envName)])
    if activeWalletPresents:
        assert cli._activeWallet is not None
        assert len(cli._activeWallet.identifiers) == identifiers
    else:
        assert cli._activeWallet is None


def switchEnv(newEnvName, do, cli, checkIfWalletRestored=False,
              restoredWalletKeyName=None, restoredIdentifiers=0):
    walletFilePath = getWalletFilePath(cli)
    do('connect {}'.format(newEnvName), within=5,
       expect=["Connected to {}".format(newEnvName)])
    # check wallet should have been persisted
    checkWalletFilePersisted(walletFilePath)
    if checkIfWalletRestored:
        checkWalletRestored(restoredWalletKeyName, cli, restoredIdentifiers)


def testSaveAndRestoreWallet(do, be, cliForMultiNodePools):
    be(cliForMultiNodePools)
    # No wallet should have been restored
    assert cliForMultiNodePools._activeWallet is None

    connectTo("pool1", do, cliForMultiNodePools,
              activeWalletPresents=True, identifiers=0)

    createNewKey(do, cliForMultiNodePools, keyringName="Default")

    switchEnv("pool2", do, cliForMultiNodePools, checkIfWalletRestored=False)

    createNewKey(do, cliForMultiNodePools, keyringName="Default")

    switchEnv("pool1", do, cliForMultiNodePools, checkIfWalletRestored=True,
              restoredWalletKeyName="Default", restoredIdentifiers=1)

    createNewKeyring("mykr1", do)
    createNewKey(do, cliForMultiNodePools, keyringName="mykr1")

    switchEnv("pool2", do, cliForMultiNodePools, checkIfWalletRestored=True,
              restoredWalletKeyName="Default", restoredIdentifiers=1)



