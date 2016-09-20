import pytest


def prompt_is(prompt):
    def x(cli):
        assert cli.currPromptText == prompt
    return x


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

    do('new keyring Faber', expect=['New keyring Faber created',
                                    'Active keyring set to "Faber"'])
    seed = 'Faber000000000000000000000000000'
    idr = '3W2465HP3OUPGkiNlTMl2iZ+NiMZegfUFIsl8378KH4='

    do('new key with seed ' + seed, expect=['Key created in keyring Faber',
                                            'Identifier for key is ' + idr,
                                            'Current identifier set to ' + idr])

