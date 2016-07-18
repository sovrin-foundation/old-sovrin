import pytest

from plenum.client.signer import SimpleSigner
from plenum.test.eventually import eventually
from sovrin.test.cli.helper import newCLI, checkGetNym


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


@pytest.fixture("module")
def nymAdded(nodesCli, looper, stewardCli, sponsorSigner):
    """
    Assume steward is created, create a sponsor an then from the sponsor cli
    create a user
    """
    stewardCli.enterCmd("send NYM dest={} role=SPONSOR"
                        .format(sponsorSigner.verstr))

    def chk():
        assert "Adding nym" in stewardCli.lastCmdOutput

    looper.run(eventually(chk, retryWait=1, timeout=5))


def testSendNym(nymAdded):
    pass


def testGetNym(stewardCli, looper, sponsorSigner, nymAdded):
    looper.run(eventually(checkGetNym, stewardCli, sponsorSigner.verstr,
                          retryWait=1, timeout=5))


@pytest.mark.skipif(True, reason="CLI command not implemented")
def testSendAttrib(nodesCli, looper, stewardCli, sponsorSigner, attrib):
    """
    Assume steward is created, sponsor is created, steward adds attribute
    for sponsor
    """
    stewardCli.enterCmd("send ATTRIB dest={} raw={}".format(
        sponsorSigner.verstr, attrib))

    def chk():
        assert "Adding attrib" in stewardCli.lastCmdOutput

    looper.run(eventually(chk, retryWait=1, timeout=5))
