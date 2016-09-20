import pytest
from plenum.common.raet import initLocalKeep
from plenum.test.eventually import eventually
from sovrin.common.plugin_helper import writeAnonCredPlugin

import plenum

plenum.common.util.loggingConfigured = False

from plenum.common.looper import Looper
from plenum.test.cli.helper import newKeyPair, checkAllNodesStarted, \
    checkCmdValid
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


@pytest.fixture(scope="module")
def CliBuilder(tdir, tdirWithPoolTxns, tdirWithDomainTxns, tconf):
    def _(subdir, looper=None):
        def new():
            return newCLI(looper,
                          tdir,
                          subDirectory=subdir,
                          conf=tconf,
                          poolDir=tdirWithPoolTxns,
                          domainDir=tdirWithDomainTxns)
        if looper:
            yield new()
        else:
            with Looper(debug=False) as looper:
                yield new()
    return _


@pytest.yield_fixture(scope="module")
def poolCLI_baby(CliBuilder):
    yield from CliBuilder("pool")


@pytest.fixture(scope="module")
def poolCLI(poolCLI_baby, poolTxnData, poolTxnNodeNames):
    seeds = poolTxnData["seeds"]
    for nName in poolTxnNodeNames:
        initLocalKeep(nName,
                      poolCLI_baby.basedirpath,
                      seeds[nName],
                      override=True)
    return poolCLI_baby


@pytest.fixture(scope="module")
def poolNodesCreated(poolCLI, poolTxnNodeNames):
    ensureNodesCreated(poolCLI, poolTxnNodeNames)
    return poolCLI


@pytest.fixture("module")
def ctx():
    """
    Provides a simple container for test context. Assists with 'be' and 'do'.
    """
    return {}


@pytest.fixture("module")
def be(ctx):
    """
    Fixture that is a 'be' function that closes over the test context.
    'be' allows to change the current cli in the context.
    """
    def x(cli):
        ctx['current_cli'] = cli
    return x


@pytest.fixture("module")
def do(ctx):
    """
    Fixture that is a 'do' function that closes over the test context
    'do' allows to call the do method of the current cli from the context.
    """
    def _(attempt, expect=None, within=None, mapper=None, not_expect=None):
        cli = ctx['current_cli']
        attempt = attempt.format(**mapper) if mapper else attempt
        checkCmdValid(cli, attempt)

        def check():
            nonlocal expect
            nonlocal not_expect

            def chk(obj, parity=True):
                if not obj:
                    return
                if isinstance(obj, str) or callable(obj):
                    obj = [obj]
                for e in obj:
                    if isinstance(e, str):
                        e = e.format(**mapper) if mapper else e
                        if parity:
                            assert e in cli.lastCmdOutput
                        else:
                            assert e not in cli.lastCmdOutput
                    elif callable(e):
                        # callables should raise exceptions to signal an error
                        if parity:
                            e(cli)
                        else:
                            try:
                                e(cli)
                            except:
                                continue
                            raise RuntimeError("did not expect success")
                    else:
                        raise AttributeError("only str, callable, or "
                                             "collections of str and callable "
                                             "are allowed")
            chk(expect)
            chk(not_expect, False)
        if within:
            cli.looper.run(eventually(check, timeout=within))
        else:
            check()
    return _


