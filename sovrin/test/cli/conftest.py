import pytest
from plenum.common.raet import initLocalKeep
from sovrin.common.plugin_helper import writeAnonCredPlugin

import plenum

plenum.common.util.loggingConfigured = False

from plenum.common.looper import Looper
from plenum.test.cli.helper import newKeyPair, checkAllNodesStarted
from plenum.test.cli.conftest import nodeRegsForCLI, nodeNames


from sovrin.common.util import getConfig
from sovrin.test.cli.helper import newCLI, ensureNodesCreated

config = getConfig()


@pytest.yield_fixture(scope="module")
def looper():
    with Looper(debug=False) as l:
        yield l


# TODO: Probably need to remove
@pytest.fixture("module")
def nodesCli(looper, tdir, nodeNames):
    cli = newCLI(looper, tdir)
    cli.enterCmd("new node all")
    checkAllNodesStarted(cli, *nodeNames)
    return cli


@pytest.fixture("module")
def cli(looper, tdir):
    return newCLI(looper, tdir)


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


@pytest.yield_fixture(scope="module")
def poolCLI(tdir, poolTxnData, poolTxnNodeNames, tdirWithPoolTxns,
            tdirWithDomainTxns, tconf):
    with Looper(debug=False) as looper:
        cli = newCLI(looper, tdir, subDirectory="pool", conf=tconf,
                     poolDir=tdirWithPoolTxns, domainDir=tdirWithDomainTxns)
        seeds = poolTxnData["seeds"]
        for nName in poolTxnNodeNames:
            initLocalKeep(nName, cli.basedirpath, seeds[nName], override=True)
        yield cli


@pytest.fixture(scope="module")
def poolNodesCreated(poolCLI, poolTxnNodeNames):
    ensureNodesCreated(poolCLI, poolTxnNodeNames)
    return poolCLI
