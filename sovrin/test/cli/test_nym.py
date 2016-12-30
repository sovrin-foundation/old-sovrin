import pytest
from plenum.common.signer_simple import SimpleSigner
from plenum.common.txn import TARGET_NYM
from plenum.common.eventually import eventually

from sovrin.test.cli.helper import newCLI, checkGetNym, chkNymAddedOutput


@pytest.fixture("module")
def stewardCli(nodeRegsForCLI, looper, tdir):
    return newCLI(nodeRegsForCLI, looper, tdir)


@pytest.fixture("module")
def sponsorSigner():
    return SimpleSigner()


@pytest.fixture("module")
def attrib():
    return '{"name": "Tyler"}'


@pytest.yield_fixture(scope="module")
def sponsorCli(CliBuilder):
    yield from CliBuilder("sponsor")


@pytest.fixture("module")
def nymAdded(nodesCli, looper, stewardCli, sponsorSigner):
    """
    Assume steward is created, create a sponsor an then from the sponsor cli
    create a user
    """
    nym = sponsorSigner.verstr
    stewardCli.enterCmd("send NYM dest={} role=SPONSOR".format(nym))
    looper.run(eventually(chkNymAddedOutput, stewardCli, nym, retryWait=1,
                          timeout=5))


@pytest.mark.skipif(True, reason="Obsolete implemtation")
def testSendNym(nymAdded):
    pass


@pytest.mark.skipif(True, reason="Obsolete implemtation")
def testGetNym(nymAdded, stewardCli, looper, sponsorSigner):
    nym = sponsorSigner.verstr
    stewardCli.enterCmd("send GET_NYM {dest}={nym}".format(dest=TARGET_NYM,
                                                           nym=nym))
    looper.run(eventually(checkGetNym, stewardCli, nym,
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
