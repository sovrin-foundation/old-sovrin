import json

import pytest
from plenum.client.signer import SimpleSigner
from sovrin.test.cli.helper import getFileLines


def prompt_is(prompt):
    def x(cli):
        assert cli.currPromptText == prompt
    return x


@pytest.yield_fixture(scope="module")
def faberCLI(CliBuilder):
    yield from CliBuilder("faber")


@pytest.fixture(scope="module")
def poolNodesStarted(be, do, poolCLI):
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
    return poolCLI


@pytest.fixture(scope="module")
def faberKeyCreated(be, do, faberCLI):
    be(faberCLI)

    do('prompt FABER', expect=prompt_is('FABER'))

    do('new keyring Faber', expect=['New keyring Faber created',
                                    'Active keyring set to "Faber"'
                                    ])
    faberSeed = 'Faber000000000000000000000000000'
    faberIdr = '3W2465HP3OUPGkiNlTMl2iZ+NiMZegfUFIsl8378KH4='

    do('new key with seed ' + faberSeed, expect=['Key created in keyring Faber',
                                                 'Identifier for key is ' +
                                                 faberIdr,
                                                 'Current identifier set to ' +
                                                 faberIdr])
    return faberCLI



@pytest.fixture(scope="module")
def philKeyCreated(be, do, philCLI):
    be(philCLI)
    do('prompt Phil', expect=prompt_is('Phil'))

    do('new keyring Phil', expect=['New keyring Phil created',
                                   'Active keyring set to "Phil"'])

    mapper = {
        'seed': '11111111111111111111111111111111',
        'idr': 'SAdaWX5yGhVuLgeZ3lzAxTJNxufq8c3UYlCGjsUyFd0='}
    do('new key with seed {seed}', expect=['Key created in keyring Phil',
                                           'Identifier for key is {idr}',
                                           'Current identifier set to {idr}'],
       mapper=mapper)

    return philCLI


@pytest.fixture(scope="module")
def faberAddedByPhil(be, do, poolNodesStarted, philKeyCreated,
                     connectedToTest, nymAddedOut, faberMap):
    philCLI = philKeyCreated
    be(philCLI)
    do('connect test',          within=3,
                                expect=connectedToTest, mapper=faberMap)

    do('send NYM dest={target} role=SPONSOR',
       within=2,
       expect=nymAddedOut, mapper=faberMap)
    return philCLI


@pytest.fixture(scope="module")
def aliceWithKeyring(be, do, aliceCli, newKeyringOut, aliceMap):
    be(aliceCli)

    do('prompt ALICE', expect=prompt_is('ALICE'))

    do('new keyring Alice', expect=newKeyringOut, mapper=aliceMap)
    return aliceCli


def testNotConnected(be, do, aliceWithKeyring, notConnectedStatus):
    aliceCLI = aliceWithKeyring
    be(aliceCLI)
    do('status',                        expect=notConnectedStatus)


def testShowInviteNotExists(be, do, aliceWithKeyring, fileNotExists, faberMap):
    aliceCLI = aliceWithKeyring
    be(aliceCLI)
    do('show {invite-not-exists}', expect=fileNotExists, mapper=faberMap)


def testShowInviteExists(be, do, aliceWithKeyring, faberMap):
    aliceCLI = aliceWithKeyring
    be(aliceCLI)
    faberInviteContents = getFileLines(faberMap.get("invite"))
    do('show {invite}', expect=faberInviteContents,
       mapper=faberMap)


def testLoadInviteNotExists(be, do, aliceWithKeyring, fileNotExists, faberMap):
    aliceCLI = aliceWithKeyring
    be(aliceCLI)
    do('load {invite-not-exists}', expect=fileNotExists, mapper=faberMap)


@pytest.fixture(scope="module")
def faberInviteLoadedByAlice(be, do, aliceWithKeyring, loadInviteOut,
                              faberMap):
    aliceCLI = aliceWithKeyring
    be(aliceCLI)
    do('load {invite}', expect=loadInviteOut, mapper=faberMap)
    return aliceCLI


def testLoadInviteExists(faberInviteLoadedByAlice):
    pass


def testShowLinkNotExists(be, do, aliceWithKeyring, linkNotExists, faberMap):
    aliceCLI = aliceWithKeyring
    be(aliceCLI)
    do('show link {inviter-not-exists}',
                                        expect=linkNotExists,
                                        mapper=faberMap)


def testShowLinkExists(be, do, aliceWithKeyring, showUnSyncedLinkOut, faberMap):
    aliceCLI = aliceWithKeyring
    be(aliceCLI)
    do('show link {inviter}', expect=showUnSyncedLinkOut,
       mapper=faberMap)


def testSyncLinkNotExists(be, do, aliceWithKeyring, linkNotExists, faberMap):
    aliceCLI = aliceWithKeyring
    be(aliceCLI)
    do('sync {inviter-not-exists}', expect=linkNotExists, mapper=faberMap)


def testFaberInviteSyncWhenNotConnected(be, do, aliceWithKeyring,
                                        faberInviteLoadedByAlice,
                                        syncWhenNotConnected,
                                        faberMap):
    aliceCLI = aliceWithKeyring
    be(aliceCLI)
    do('sync {inviter}', expect=syncWhenNotConnected,
       mapper=faberMap)


@pytest.fixture(scope="module")
def faberInviteSyncedWithoutEndpoint(be, do, aliceWithKeyring, faberMap,
                                     faberInviteLoadedByAlice, poolNodesStarted,
                                     connectedToTest,
                                     syncLinkOutWithoutEndpoint):
    aliceCLI = aliceWithKeyring
    be(aliceCLI)

    do('connect test',                  within=3,
                                        expect=connectedToTest,
                                        mapper=faberMap)

    do('sync {inviter}',                within=2,
                                        expect=syncLinkOutWithoutEndpoint,
                                        mapper=faberMap)
    return aliceCLI


def testSyncFaberInvite(faberInviteSyncedWithoutEndpoint):
    pass


def testShowSyncedInvite(be, do, aliceWithKeyring, faberInviteSyncedWithoutEndpoint,
                         linkNotYetSynced, showSyncedLinkWithoutEndpointOut,
                         faberMap):
    aliceCLI = faberInviteSyncedWithoutEndpoint

    be(aliceCLI)

    do('show link {inviter}', expect=showSyncedLinkWithoutEndpointOut,
       not_expect=linkNotYetSynced,
       mapper=faberMap)


@pytest.fixture(scope="module")
def faberWithEndpointAdded(be, do, faberAddedByPhil,
                           faberMap, attrAddedOut):
    philCLI = faberAddedByPhil
    be(philCLI)
    # I had to give two open/close curly braces in raw data
    # to avoid issue in mapping
    do('send ATTRIB dest={target} raw={{"endpoint": "0.0.0.0:1212"}}',
                                        within=2,
                                        expect=attrAddedOut,
                                        mapper=faberMap)
    return philCLI


def testEndpointAddedForFaber(faberWithEndpointAdded):
    pass


@pytest.fixture(scope="module")
def faberInviteSyncedWithEndpoint(be, do, aliceWithKeyring, faberMap,
                                  faberInviteSyncedWithoutEndpoint,
                                  faberWithEndpointAdded,
                                  syncLinkOutWithEndpoint,
                                  poolNodesStarted):
    aliceCLI = faberInviteSyncedWithoutEndpoint
    be(aliceCLI)

    do('sync {inviter}',                within=2,
                                        expect=syncLinkOutWithEndpoint,
                                        mapper=faberMap)
    return aliceCLI


def testFaberInviteSyncWithEndpoint(faberInviteSyncedWithEndpoint):
    pass


def testShowSyncedInviteWithEndpoint(be, do, faberInviteSyncedWithEndpoint,
                                     showSyncedLinkWithEndpointOut, faberMap):
    aliceCLI = faberInviteSyncedWithEndpoint
    be(aliceCLI)
    do('show link {inviter}',           expect=showSyncedLinkWithEndpointOut,
                                             mapper=faberMap)


def testAcceptNotExistsLink(be, do, aliceWithKeyring, linkNotExists, faberMap):
    aliceCLI = aliceWithKeyring
    be(aliceCLI)
    do('accept invitation {inviter-not-exists}', expect=linkNotExists,
       mapper=faberMap)


# TODO: Below tests works fine individually, when run inside whole suite,
# then, it fails (seems, cli state doesn't get clear)
def testAcceptUnSyncedInviteWhenNotConnected(be, do,
                                             faberInviteLoadedByAlice,
                                             acceptUnSyncedLinkWhenNotConnected,
                                             faberMap):
    aliceCLI = faberInviteLoadedByAlice
    be(aliceCLI)
    do('accept invitation {inviter}', expect=acceptUnSyncedLinkWhenNotConnected,
                                      mapper=faberMap)


def testAcceptUnSyncedInviteWhenConnected(be, do, faberInviteLoadedByAlice,
                                          acceptUnSyncedWhenConnected,
                                          faberMap, connectedToTest,
                                          poolNodesStarted):
    aliceCLI = faberInviteLoadedByAlice
    be(aliceCLI)
    if not aliceCLI._isConnectedToAnyEnv():
        do('connect test',                  within=3,
                                            expect=connectedToTest,
                                            mapper=faberMap)

    do('accept invitation {inviter}',   within=3,
                                        expect=acceptUnSyncedWhenConnected,
                                        mapper=faberMap)


def testAcceptInvitationResponse(faberInviteSyncedWithEndpoint, faberKeyCreated):
    aliceCLI = faberInviteSyncedWithEndpoint
    faberCLI = faberKeyCreated
    signer = SimpleSigner(identifier=faberCLI.activeWallet.defaultId)
    msg = """{
        "type":"AVAIL_CLAIM_LIST",
        "identifier": "<identifier>",
        "claimsList": [ {
            "name": "Transcript",
            "version": "1.2",
            "definition": {
                "attributes": {
                    "studentName": "string",
                    "ssn": "int",
                    "degree": "string",
                    "year": "string",
                    "status": "string"
                }
            }
        } ]
      }""".replace("<identifier>", str(faberCLI.activeWallet.defaultId))

    acceptInviteResp = json.loads(msg)

    signature = signer.sign(acceptInviteResp)
    acceptInviteResp["signature"] = signature
    aliceCLI._handleAcceptInviteResponse(acceptInviteResp)
