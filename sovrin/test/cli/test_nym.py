import pytest

from sovrin.common.txn import USER
from sovrin.test.cli.helper import sendNym


@pytest.fixture("module")
def stewardCli():
    pass


@pytest.fixture("module")
def sponsorCli():
    pass


def testSendNym(cli, stewardCreated, newKeyPairCreated):
    sendNym(cli, newKeyPairCreated, USER)

