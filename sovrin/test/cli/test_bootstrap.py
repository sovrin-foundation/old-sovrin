import pytest

from plenum.test.cli.helper import checkCmdValid
from plenum.test.eventually import eventually


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
    def _(attempt, expect, within=None):
        cli = ctx['current_cli']
        checkCmdValid(cli, attempt)

        def check():
            nonlocal expect
            if isinstance(expect, str) or callable(expect):
                expect = [expect]
            for e in expect:
                if isinstance(e, str):
                    assert e in cli.lastCmdOutput
                elif callable(e):
                    # callables should raise exceptions to signal an error
                    e(cli)
                else:
                    raise AttributeError("only str, callable, or collections "
                                         "of str and callable are allowed")
        if within:
            cli.looper.run(eventually(check, timeout=within))
        else:
            check()
    return _


@pytest.yield_fixture(scope="module")
def faberCLI(CliBuilder):
    yield from CliBuilder("faber")


def test(poolCLI, faberCLI, be, do):

    be(poolCLI)

    do('new node all', within=10,
                       expect=['Alpha now connected to Beta',
                               'Alpha now connected to Gamma',
                               'Alpha now connected to Delta',
                               'Beta now connected to Alpha',
                               'Beta now connected to Gamma',
                               'Beta now connected to Delta',
                               'Gamma now connected to Alpha',
                               'Gamma now connected to Beta',
                               'Gamma now connected to Delta',
                               'Delta now connected to Alpha',
                               'Delta now connected to Beta',
                               'Delta now connected to Gamma'])

    be(faberCLI)

    do('prompt FABER', expect=prompt_is('FABER'))

    do('new keyring Faber', expect=['New wallet Faber created',
                                    'Active wallet set to "Faber"'])
    seed = 'Faber000000000000000000000000000'
    idr = '3W2465HP3OUPGkiNlTMl2iZ+NiMZegfUFIsl8378KH4='

    do('new key with seed ' + seed, expect=['Key created in wallet Faber',
                                            'Identifier for key is ' + idr,
                                            'Current identifier set to ' + idr])

