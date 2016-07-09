import pytest

from sovrin.common.txn import USER
from sovrin.test.cli.helper import sendNym, TestCLI, newCLI


@pytest.fixture("module")
def nodesCli(nodeRegsForCLI, looper, tdir):
    return newCLI(nodeRegsForCLI, looper, tdir)


@pytest.fixture("module")
def stewardCli(nodeRegsForCLI, looper, tdir):
    return newCLI(nodeRegsForCLI, looper, tdir)


@pytest.fixture("module")
def sponsorCli(nodeRegsForCLI, looper, tdir):
    return newCLI(nodeRegsForCLI, looper, tdir)


def testSendNym(cli: TestCLI, stewardCreated, newKeyPairCreated):
    nym = newKeyPairCreated
    sendNym(cli, nym, USER)
    assert 'Invalid command' not in cli.printeds
