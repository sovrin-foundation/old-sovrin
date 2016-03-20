import pytest

from plenum.client.signer import SimpleSigner

from sovrin.common.txn import getGenesisTxns
from sovrin.test.helper import clientFromSigner, TestNodeSet, genTestClient

from plenum.test.conftest import getValueFromModule

from plenum.test.conftest import tdir, looper, counter, unstartedLooper, \
    nodeReg, up, ready, keySharedNodes


@pytest.fixture(scope="module")
def genesisTxns():
    return getGenesisTxns()


@pytest.yield_fixture(scope="module")
def nodeSet(request, tdir, nodeReg):
    primaryDecider = getValueFromModule(request, "PrimaryDecider", None)
    with TestNodeSet(nodeReg=nodeReg, tmpdir=tdir,
                     primaryDecider=primaryDecider) as ns:
        yield ns


@pytest.fixture(scope="module")
def genned(nodeSet, genesisTxns):
    for n in nodeSet:
        n.addGenesisTxns(genesisTxns)


@pytest.fixture(scope="module")
def startedNodes(nodeSet, looper):
    for n in nodeSet:
        n.start(looper.loop)
    return nodeSet


@pytest.fixture(scope="module")
def client1Signer():
    seed = b'client1Signer secret key........'
    signer = SimpleSigner(seed=seed)
    assert signer.verstr == 'TuIpuBcx6P4S0Ez5LUr3HVpWERVHK56XONixonwcAf4='
    return signer


@pytest.fixture(scope="module")
def client1(client1Signer, looper, nodeSet, tdir, up):
    client = genTestClient(nodeSet, signer=client1Signer, tmpdir=tdir)
    looper.add(client)
    looper.run(client.ensureConnectedToNodes())
    return client


@pytest.fixture(scope="module")
def stewardSigner():
    seed = b'is a pit a seed, or somepin else'
    signer = SimpleSigner(seed=seed)
    assert signer.verstr == 'OP2h59vBVQerRi6FjoOoMhSTv4CAemeEg4LPtDHaEWw='
    return signer


@pytest.fixture(scope="module")
def steward(looper, nodeSet, tdir, up, stewardSigner):
    s = genTestClient(nodeSet, signer=stewardSigner, tmpdir=tdir)
    looper.add(s)
    looper.run(s.ensureConnectedToNodes())
    return s


@pytest.fixture(scope="module")
def sponsorSigner():
    seed = b'sponsors are people too.........'
    signer = SimpleSigner(seed=seed)
    return signer


@pytest.fixture(scope="module")
def sponsor(looper, nodeSet, tdir, up, sponsorSigner):
    return clientFromSigner(sponsorSigner, looper, nodeSet, tdir)
