import pytest
from sovrin.test.cli.helper import getFileLines


def prompt_is(prompt):
    def x(cli):
        assert cli.currPromptText == prompt
    return x


@pytest.yield_fixture(scope="module")
def faberCLI(CliBuilder):
    yield from CliBuilder("faber")


def test(looper, poolCLI, philCLI, faberCLI, aliceCli, be, do, fileNotExists,
         notConnectedStatus, loadInviteOut, linkNotExists, showUnSyncedLinkOut,
         syncWhenNotConnectedStatus, showSyncedLinkWithoutEndpointOut,
         connectedToTest, syncLinkOutWithoutEndpoint, newKeyringOut,
         linkNotYetSynced, attrAddedOut, nymAddedOut, syncLinkOutWithEndpoint,
         showSyncedLinkWithEndpointOut, aliceMap, faberMap):


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
                                                'Active keyring set to "Faber"'
                                                ])
    faberSeed = 'Faber000000000000000000000000000'
    faberIdr = '3W2465HP3OUPGkiNlTMl2iZ+NiMZegfUFIsl8378KH4='

    do('new key with seed ' + faberSeed,expect=['Key created in keyring Faber',
                                                'Identifier for key is ' +
                                                    faberIdr,
                                                'Current identifier set to ' +
                                                    faberIdr])

    be(philCLI)
    do('prompt Phil',                   expect=prompt_is('Phil'))

    do('new keyring Phil',              expect=['New keyring Phil created',
                                                'Active keyring set to "Phil"'])

    mapper = {
        'seed': '11111111111111111111111111111111',
        'idr': 'SAdaWX5yGhVuLgeZ3lzAxTJNxufq8c3UYlCGjsUyFd0='}
    do('new key with seed {seed}', expect=['Key created in keyring Phil',
                                           'Identifier for key is {idr}',
                                           'Current identifier set to {idr}'],
                                   mapper=mapper)

    do('connect test',             within=2,
                                   expect=connectedToTest, mapper=faberMap)

    do('send NYM dest={target} role=SPONSOR',
                                        within=2,
                                        expect=nymAddedOut, mapper=faberMap)

    be(aliceCli)

    do('prompt ALICE',                  expect=prompt_is('ALICE'))

    do('new keyring Alice',             expect=newKeyringOut, mapper=aliceMap)

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

    do('show link {inviter}',           expect=showUnSyncedLinkOut,
                                        mapper=faberMap)

    do('sync {inviter-not-exists}',     expect=linkNotExists, mapper=faberMap)

    do('sync {inviter}',                expect=syncWhenNotConnectedStatus,
                                        mapper=faberMap)

    do('connect test',                  within=2,
                                        expect=connectedToTest,
                                        mapper=faberMap)

    do('sync {inviter}',                within=2,
                                        expect=syncLinkOutWithoutEndpoint,
                                        mapper=faberMap)

    do('show link {inviter}',           expect=showSyncedLinkWithoutEndpointOut,
                                        not_expect=linkNotYetSynced,
                                        mapper=faberMap)

    be(philCLI)
    # I had to give two open/close curly braces in raw data
    # to avoid issue in mapping
    do('send ATTRIB dest={target} raw={{"endpoint": "0.0.0.0:1212"}}',
                                        within=2,
                                        expect=attrAddedOut,
                                        mapper=faberMap)

    be(aliceCli)

    do('sync {inviter}',                within=2,
                                        expect=syncLinkOutWithEndpoint,
                                        mapper=faberMap)

    do('show link {inviter}',           expect=showSyncedLinkWithEndpointOut,
                                        mapper=faberMap)
