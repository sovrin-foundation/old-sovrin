import pytest

from sovrin.common.txn import USER
from sovrin.test.cli.helper import sendNym, TestCli


@pytest.fixture("module")
def stewardCli():
    pass


@pytest.fixture("module")
def sponsorCli():
    pass


def testSendNym(cli: TestCli, stewardCreated, newKeyPairCreated):
    nym = newKeyPairCreated
    sendNym(cli, nym, USER)
    assert 'Invalid command' not in cli.printeds[1]['msg']
