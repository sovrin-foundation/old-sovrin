from binascii import unhexlify

import pytest
from plenum.client.signer import SimpleSigner
from plenum.test.conftest import getValueFromModule
from plenum.test.conftest import tdir, looper, unstartedLooper, counter, \
    nodeReg, keySharedNodes, replied1, up, ready, committed1, prepared1, \
    preprepared1, propagated1, reqAcked1, request1, sent1, faultyNodes

from sovrin.common.txn import getGenesisTxns
from sovrin.test.helper import TestNodeSet, genTestClient, clientFromSigner


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
def client1(looper, nodeSet, tdir, up):
    client = genTestClient(nodeSet, tmpdir=tdir)
    looper.add(client)
    looper.run(client.ensureConnectedToNodes())
    return client


@pytest.fixture(scope="module")
def stewardSigner():
    seed = b'84198c0032e3e7658f787e886991e188659b244ab9a093ed0ca14246a01e6907'
    signer = SimpleSigner('steward', unhexlify(seed))
    return signer


@pytest.fixture(scope="module")
def steward(looper, nodeSet, tdir, up, stewardSigner):
    s = genTestClient(nodeSet, signer=stewardSigner, tmpdir=tdir)
    looper.add(s)
    looper.run(s.ensureConnectedToNodes())
    return s


@pytest.fixture(scope="module")
def sponsorSigner():
    seed = b'8f787e886991e188659b244ab9a093ed0ca184198c0032e3e7654246a01e6907'
    signer = SimpleSigner('sponsor', unhexlify(seed))
    return signer


@pytest.fixture(scope="module")
def sponsor(looper, nodeSet, tdir, up, sponsorSigner):
    return clientFromSigner(sponsorSigner, looper, nodeSet, tdir)
