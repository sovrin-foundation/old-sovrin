import pytest
from sovrin.test.cli.conftest import getFileLines


def prompt_is(prompt):
    def x(cli):
        assert cli.currPromptText == prompt
    return x


@pytest.yield_fixture(scope="module")
def faberCLI(CliBuilder):
    yield from CliBuilder("faber")


def test(poolCLI, faberCLI, aliceCli, be, do, fileNotExists,
         notConnectedStatus, loadInviteOut, linkNotExists, showLinkOut,
         syncWhenNotConnectedStatus, faberMap):


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

    do('prompt FABER',                  expect=prompt_is('FABER'))

    do('new keyring Faber',             expect=['New keyring Faber created',
                                                'Active keyring set to "Faber"'])
    seed = 'Faber000000000000000000000000000'
    idr = '3W2465HP3OUPGkiNlTMl2iZ+NiMZegfUFIsl8378KH4='

    do('new key with seed ' + seed,     expect=['Key created in keyring Faber',
                                            'Identifier for key is ' + idr,
                                            'Current identifier set to ' + idr])

    be(aliceCli)

    do('prompt ALICE',                  expect=prompt_is('ALICE'))

    do('status',                        expect=notConnectedStatus)

    do('show {invite-not-exists}',      expect=fileNotExists, mapper=faberMap)

    faberInviteContents = getFileLines(faberMap.get("invite"))
    do('show {invite}',                 expect=faberInviteContents,
                                        mapper=faberMap)

    do('load {invite-not-exists}',      expect=fileNotExists, mapper=faberMap)

    do('load {invite}',                 expect=loadInviteOut, mapper=faberMap)

    do('show link {inviter-not-exists}',
                                        expect=linkNotExists,
                                        mapper=faberMap)

    do('show link {inviter}',           expect=showLinkOut, mapper=faberMap)

    do('sync {inviter-not-exists}',     expect=linkNotExists, mapper=faberMap)

    do('sync {inviter}',                expect=syncWhenNotConnectedStatus,
                                        mapper=faberMap)