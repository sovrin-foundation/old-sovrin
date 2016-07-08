import pytest

import plenum
from plenum.common.looper import Looper
from plenum.test.cli.conftest import nodeRegsForCLI, createAllNodes
from plenum.common.looper import Looper
from sovrin.common.util import getConfig

plenum.common.util.loggingConfigured = False

from sovrin.test.cli.helper import newCLI

config = getConfig()

from plenum.test.cli.helper import newKeyPair


@pytest.yield_fixture(scope="module")
def looper():
    with Looper(debug=False) as l:
        yield l


@pytest.fixture("module")
def cli(nodeRegsForCLI, looper, tdir):
    return newCLI(nodeRegsForCLI, looper, tdir)


@pytest.fixture(scope="module")
def stewardCreated(cli, createAllNodes, stewardSigner):
    steward = cli.newClient(clientName="steward", signer=stewardSigner)
    for node in cli.nodes.values():
        node.whitelistClient(steward.name)
    cli.looper.run(steward.ensureConnectedToNodes())
    return steward


@pytest.fixture(scope="module")
def newKeyPairCreated(cli):
    return newKeyPair(cli)
