import pytest
from plenum.test.conftest import getValueFromModule
from plenum.test.conftest import tdir, looper, unstartedLooper, counter, \
    nodeReg, keySharedNodes

from sovirin.test.helper import TestNodeSet, genTestClient


@pytest.yield_fixture(scope="module")
def nodeSet(request, tdir, nodeReg):
    primaryDecider = getValueFromModule(request, "PrimaryDecider", None)
    with TestNodeSet(nodeReg=nodeReg, tmpdir=tdir,
                     primaryDecider=primaryDecider) as ns:
        yield ns


@pytest.fixture(scope="module")
def startedNodes(nodeSet, looper):
    for n in nodeSet:
        n.start(looper.loop)
    return nodeSet


@pytest.fixture(scope="module")
def client1(looper, nodeSet, tdir, up):
    client = genTestClient(nodeSet, tmpdir=tdir)
    looper.add(client)
    looper.run(client.ensureConnectedToNodes())
    return client