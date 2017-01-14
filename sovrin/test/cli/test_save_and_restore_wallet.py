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
    assert "keyring_default_test" == walletFileName
    assert "default" == Cli.getWalletKeyName(walletFileName)

    # User creates new wallet (keyring)
    walletFileName = Cli.getPersistentWalletFileName(
        cliName=cliName, currPromptText="sovrin@test",
        activeWalletName="MyVault")
    assert "keyring_myvault_test" == walletFileName
    assert "myvault" == Cli.getWalletKeyName(walletFileName)


def checkWalletFilePersisted(filePath):
    assert os.path.exists(filePath)


def checkWalletRestore(be, do, cli, cmd, expectedMsg, mapper):
    # check message of saved keyring alice restored
    be(cli)
    do(cmd, within=3,
       expect=expectedMsg,
       mapper=mapper)


def getWalletFilePath(cli):
    activeWalletName = cli._activeWallet.name if cli._activeWallet else ""
    fileName = Cli.getPersistentWalletFileName(
        cli.name, cli.currPromptText, activeWalletName)
    return Cli.getWalletFilePath(cli.config.baseDir, fileName)


def testSaveAndRestoreWallet(do, be, cliForMultiNodePools):
    be(cliForMultiNodePools)
    # No wallet should have been restored
    assert cliForMultiNodePools._activeWallet is None

    # connect to any valid environment
    do('connect pool1', within=5, expect=["Connected to pool1"])
    assert cliForMultiNodePools._activeWallet is not None
    # No wallet should have been restored
    assert len(cliForMultiNodePools._activeWallet.identifiers) == 0

    # create key in current wallet
    do('new key', within=2, expect=["Key created in keyring Default"])
    assert len(cliForMultiNodePools._activeWallet.identifiers) == 1
    walletFilePath = getWalletFilePath(cliForMultiNodePools)
    do('connect pool2', within=5, expect=["Connected to pool2"])
    # check wallet should have been persisted
    checkWalletFilePersisted(walletFilePath)
    # create key in current wallet
    do('new key', within=2, expect=["Key created in keyring Default"])
    walletFilePath = getWalletFilePath(cliForMultiNodePools)
    do('connect pool1', within=5, expect=["Connected to pool1"])
    # check wallet should have been persisted
    checkWalletFilePersisted(walletFilePath)
    assert len(cliForMultiNodePools._activeWallet.identifiers) == 1


    # do(None, expect=prompt_is("sovrin"))
    # do('connect pool1', within=5, expect=["Connected to pool1"])
    # do(None, expect=prompt_is("sovrin@pool1"))
    # do('connect pool2', within=5, expect=["Connected to pool2"])
    # do(None, expect=prompt_is("sovrin@pool2"))
    # do('connect pool1', within=5, expect=["Connected to pool1"])
    # do(None, expect=prompt_is("sovrin@pool1"))
