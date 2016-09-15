from plenum.test.eventually import eventually
from sovrin.test.cli.helper import checkConnectedToEnv, ensureNodesCreated


def testConnectEnv(poolNodesCreated, looper):
    poolCLI = poolNodesCreated
    # Done to initialise a wallet.
    poolCLI.enterCmd("new key")

    poolCLI.enterCmd("status")
    assert "Not connected to Sovrin network" in poolCLI.lastCmdOutput
    assert "Type 'connect test' or 'connect live' to connect to a network." \
           in poolCLI.lastCmdOutput

    poolCLI.enterCmd("connect dummy")
    assert "Unknown environment dummy" in poolCLI.lastCmdOutput

    poolCLI.enterCmd("connect test")
    assert "Connecting to test" in poolCLI.lastCmdOutput
    looper.run(eventually(checkConnectedToEnv, poolCLI, retryWait=1,
                          timeout=10))
    poolCLI.enterCmd("status")
    assert "Connected to test Sovrin network" == poolCLI.lastCmdOutput
