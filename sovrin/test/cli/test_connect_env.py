from plenum.test.eventually import eventually
from sovrin.test.cli.conftest import notConnectedStatus
from sovrin.test.cli.helper import checkConnectedToEnv, ensureNodesCreated


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
