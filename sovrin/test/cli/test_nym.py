import pytest

from plenum.client.signer import SimpleSigner
from plenum.test.cli.helper import checkAllNodesStarted
from plenum.test.eventually import eventually
from sovrin.common.txn import USER
from sovrin.test.cli.helper import sendNym, TestCLI, newCLI


@pytest.fixture("module")
def stewardCli(nodeRegsForCLI, looper, tdir):
    return newCLI(nodeRegsForCLI, looper, tdir)


@pytest.fixture("module")
def sponsorSigner():
    return SimpleSigner()


@pytest.fixture("module")
def attrib():
    return '{"name": "Tyler"}'


@pytest.fixture("module")
def sponsorCli(nodeRegsForCLI, looper, tdir):
    return newCLI(nodeRegsForCLI, looper, tdir)


def testSendNym(nodesCli, looper, stewardCli, sponsorSigner):
    """
    Assume steward is created, create a sponsor an then from the sponsor cli
    create a user
    """
    stewardCli.enterCmd("send nym dest={}".format(sponsorSigner.verstr))

    def chk():
        assert "Adding nym" in ",".join(stewardCli.printeds)

    looper.run(eventually(chk, retryWait=1, timeout=5))


def testSendAttrib(nodesCli, looper, stewardCli, sponsorSigner, attrib):
    """
    Assume steward is created, sponsor is created, steward adds attribute
    for sponsor
    """
    stewardCli.enterCmd("send attrib dest={} raw={}".format(sponsorSigner.verstr
                                                            , attrib))

    def chk():
        assert "Adding attrib" in ",".join(stewardCli.printeds)

    looper.run(eventually(chk, retryWait=1, timeout=5))
