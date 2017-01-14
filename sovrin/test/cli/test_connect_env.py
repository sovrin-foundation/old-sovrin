import pytest
from plenum.common.eventually import eventually

from sovrin.test.cli.helper import checkConnectedToEnv, prompt_is


def testConnectEnv(poolNodesCreated, looper, notConnectedStatus):
    poolCLI = poolNodesCreated
    notConnectedMsgs = notConnectedStatus
    # Done to initialise a wallet.
    poolCLI.enterCmd("new key")

    poolCLI.enterCmd("status")
    for msg in notConnectedMsgs:
        assert msg in poolCLI.lastCmdOutput

    poolCLI.enterCmd("connect dummy")
    assert "Unknown environment dummy" in poolCLI.lastCmdOutput

    poolCLI.enterCmd("connect test")
    assert "Connecting to test" in poolCLI.lastCmdOutput
    looper.run(eventually(checkConnectedToEnv, poolCLI, retryWait=1,
                          timeout=10))
    poolCLI.enterCmd("status")
    assert "Connected to test Sovrin network" == poolCLI.lastCmdOutput


def testCreateMultiPoolNodes(multiPoolNodesCreated):
    assert len(multiPoolNodesCreated) == 2


@pytest.fixture(scope="module")
def pool1(multiPoolNodesCreated):
    return multiPoolNodesCreated[0]


@pytest.fixture(scope="module")
def pool2(multiPoolNodesCreated):
    return multiPoolNodesCreated[1]


def testSusanConnectsToDifferentPools(do, be, cliForMultiNodePools):
    be(cliForMultiNodePools)
    do(None, expect=prompt_is("sovrin"))
    do('connect pool1', within=5, expect=["Connected to pool1"])
    do(None, expect=prompt_is("sovrin@pool1"))
    do('connect pool2', within=5, expect=["Connected to pool2"])
    do(None, expect=prompt_is("sovrin@pool2"))
    do('connect pool1', within=5, expect=["Connected to pool1"])
    do(None, expect=prompt_is("sovrin@pool1"))
