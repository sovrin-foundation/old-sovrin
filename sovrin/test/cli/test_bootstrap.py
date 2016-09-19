"""
Pool cli
    workon sovrin
    sovrin --noreg
    prompt PoolCli
    new node all
Faber cli
    workon sovrin
    sovrin --noreg
    new keyring Faber        # use keyring Faber (if keyring already created)
    prompt Faber
    new key with seed Faber000000000000000000000000000
Acme Corp cli
    workon sovrin
    sovrin --noreg
    new keyring Acme        # use keyring Acme (if keyring already created)
    prompt Acme
    new key with seed Acme0000000000000000000000000000
BoA cli
    workon sovrin
    sovrin --noreg
    new keyring BoA        # use keyring BoA (if keyring already created)
    prompt BoA
    new key with seed Bank0000000000000000000000000000
Steward cli
    workon sovrin
    sovrin --noreg
    new keyring Steward        # use keyring Steward (if keyring already created)
    prompt Steward
    new key with seed 000000000000000000000000Steward1

    connect test
    status
"""
import pytest

from plenum.common.looper import Looper
from plenum.test.cli.helper import checkCmdValid
from sovrin.test.cli.helper import newCLI


@pytest.fixture("module")
def ctx():
    """
    Provides a simple container for test context. Assists with 'be' and 'do'.
    """
    return {}


def prompt_is(prompt):
    def x(cli):
        assert cli.currPromptText == prompt
    return x


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
    def x(attempt, expect):
        cli = ctx['current_cli']
        checkCmdValid(cli, attempt)
        if isinstance(expect, str) or callable(expect):
            expect = [expect]
        for e in expect:
            if isinstance(e, str):
                assert e in cli.lastCmdOutput
            elif callable(e):
                # callables should raise exceptions to signal an error is found
                e(cli)
            else:
                raise AttributeError("only str, callable, or collections "
                                     "of str and callable are allowed")
    return x


@pytest.fixture(scope="module")
def CliBuilder(tdir, tdirWithPoolTxns, tdirWithDomainTxns, tconf):
    def x(subdir):
        with Looper(debug=False) as looper:
            yield newCLI(looper,
                         tdir,
                         subDirectory=subdir,
                         conf=tconf,
                         poolDir=tdirWithPoolTxns,
                         domainDir=tdirWithDomainTxns)
    return x


@pytest.yield_fixture(scope="module")
def poolCLI(CliBuilder):
    yield next(CliBuilder("pool"))


@pytest.yield_fixture(scope="module")
def faberCLI(CliBuilder):
    yield next(CliBuilder("faber"))


def testPromptChange(poolCLI, be, do):

    be(poolCLI)

    do('prompt POOL', expect=prompt_is('POOL'))

    # do('new node all', expect=['node A created...',
    #                            'node A created...'])
    #
    # be(faberCLI)
    # do('new keyring Faber', expect=['Keyring Faber created.',
    #                                 'Default keyring set to Faber.'])
    # do('prompt Faber',      expect=prompt_is('faber')),
    # do('new key with seed '
    #    'Faber00000000000'
    #    '0000000000000000',  expect='Key created blah blah')
