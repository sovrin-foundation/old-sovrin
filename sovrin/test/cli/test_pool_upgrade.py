from copy import copy

import pytest

from plenum.common.eventually import eventually
from plenum.common.txn import VERSION
from sovrin.common.txn import ACTION, CANCEL
from sovrin.test.upgrade.conftest import validUpgrade
from sovrin.test.cli.test_tutorial import poolNodesStarted
from sovrin.test.upgrade.helper import checkUpgradeScheduled, \
    checkNoUpgradeScheduled


@pytest.fixture(scope='module')
def nodeIds(poolNodesStarted):
    return next(iter(poolNodesStarted.nodes.values())).poolManager.nodeIds


@pytest.fixture(scope="module")
def vals(trusteeWallet):
    return {
        'trusteeSeed': bytes(trusteeWallet._signerById(
            trusteeWallet.defaultId).sk).decode(),
        'trusteeIdr': trusteeWallet.defaultId,
    }


@pytest.yield_fixture(scope="module")
def trusteeCLI(CliBuilder):
    yield from CliBuilder("newTrustee")


@pytest.fixture(scope="module")
def trusteeCli(be, do, vals, poolNodesStarted,
               connectedToTest, nymAddedOut, trusteeCLI):
    be(trusteeCLI)
    do('new key with seed {trusteeSeed}', expect=[
        'Identifier for key is {trusteeIdr}',
        'Current identifier set to {trusteeIdr}'],
       mapper=vals)

    if not trusteeCLI._isConnectedToAnyEnv():
        do('connect test', within=3,
           expect=connectedToTest)

    return trusteeCLI


@pytest.fixture(scope="module")
def poolUpgradeSubmitted(be, do, trusteeCli, validUpgrade, vals):
    do('send POOL_UPGRADE name={name} version={version} sha256={sha256} '
       'action={action} schedule={schedule} timeout={timeout}',
       within=10,
       expect=['Pool upgrade successful'], mapper=validUpgrade)


@pytest.fixture(scope="module")
def poolUpgradeScheduled(poolUpgradeSubmitted, poolNodesStarted, validUpgrade):
    nodes = poolNodesStarted.nodes.values()
    poolNodesStarted.looper.run(
        eventually(checkUpgradeScheduled, nodes,
                   validUpgrade[VERSION], retryWait=1, timeout=10))


@pytest.fixture(scope="module")
def poolUpgradeCancelled(poolUpgradeScheduled, be, do, trusteeCli,
                         validUpgrade, vals):
    validUpgrade = copy(validUpgrade)
    validUpgrade[ACTION] = CANCEL
    do('send POOL_UPGRADE name={name} version={version} sha256={sha256} '
       'action={action}',
       within=10,
       expect=['Pool upgrade successful'], mapper=validUpgrade)


def testPoolUpgradeSent(poolUpgradeScheduled):
    pass


def testPoolUpgradeCancelled(poolUpgradeCancelled, poolNodesStarted):
    nodes = poolNodesStarted.nodes.values()
    poolNodesStarted.looper.run(
        eventually(checkNoUpgradeScheduled,
                   nodes, retryWait=1, timeout=10))
