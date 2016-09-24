import json

import pytest
from plenum.client.signer import SimpleSigner
from sovrin.agent.faber import FaberAgent
from sovrin.test.cli.helper import getFileLines


FABER_ENDPOINT_PORT = 1212


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

    do('new node all',                  within=6,
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
def faberCli(be, do, faberCLI):
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
    return faberCLI


@pytest.fixture(scope="module")
def philCli(be, do, philCLI):
    be(philCLI)
    do('prompt Phil',                   expect=prompt_is('Phil'))

    do('new keyring Phil',              expect=['New keyring Phil created',
                                                'Active keyring set to "Phil"'])

    mapper = {
        'seed': '11111111111111111111111111111111',
        'idr': 'SAdaWX5yGhVuLgeZ3lzAxTJNxufq8c3UYlCGjsUyFd0='}
    do('new key with seed {seed}',      expect=['Key created in keyring Phil',
                                                'Identifier for key is {idr}',
                                                'Current identifier set to '
                                                '{idr}'],
       mapper=mapper)

    return philCLI


@pytest.fixture(scope="module")
def faberAddedByPhil(be, do, poolNodesStarted, philCli, connectedToTest,
                     nymAddedOut, faberMap):
    be(philCli)
    do('connect test',                  within=3,
                                        expect=connectedToTest, mapper=faberMap)

    do('send NYM dest={target} role=SPONSOR',
                                        within=2,
                                        expect=nymAddedOut, mapper=faberMap)
    return philCli


@pytest.fixture(scope="module")
def aliceCli(be, do, aliceCLI, newKeyringOut, aliceMap):
    be(aliceCLI)

    do('prompt ALICE', expect=prompt_is('ALICE'))

    do('new keyring Alice',             expect=newKeyringOut, mapper=aliceMap)
    return aliceCLI


def testNotConnected(be, do, aliceCli, notConnectedStatus):
    be(aliceCli)
    do('status',                        expect=notConnectedStatus)


def testShowInviteNotExists(be, do, aliceCli, fileNotExists, faberMap):
    be(aliceCli)
    do('show {invite-not-exists}',      expect=fileNotExists, mapper=faberMap)


def testShowInviteExists(be, do, aliceCli, faberMap):
    be(aliceCli)
    faberInviteContents = getFileLines(faberMap.get("invite"))

    do('show {invite}',                 expect=faberInviteContents,
                                        mapper=faberMap)


def testLoadInviteNotExists(be, do, aliceCli, fileNotExists, faberMap):
    be(aliceCli)
    do('load {invite-not-exists}',      expect=fileNotExists, mapper=faberMap)


@pytest.fixture(scope="module")
def faberInviteLoadedByAlice(be, do, aliceCli, loadInviteOut, faberMap):
    be(aliceCli)
    do('load {invite}',                 expect=loadInviteOut, mapper=faberMap)
    return aliceCli


def testLoadInviteExists(faberInviteLoadedByAlice):
    pass


def testShowLinkNotExists(be, do, aliceCli, linkNotExists, faberMap):
    be(aliceCli)
    do('show link {inviter-not-exists}',
                                        expect=linkNotExists,
                                        mapper=faberMap)


def testShowLinkExists(be, do, aliceCli, showUnSyncedLinkOut, faberMap):
    be(aliceCli)
    do('show link {inviter}',           expect=showUnSyncedLinkOut,
                                        mapper=faberMap)


def testSyncLinkNotExists(be, do, aliceCli, linkNotExists, faberMap):
    be(aliceCli)
    do('sync {inviter-not-exists}',     expect=linkNotExists, mapper=faberMap)


def testSyncWhenNotConnected(be, do, aliceCli, faberMap,
                                        faberInviteLoadedByAlice,
                                        syncWhenNotConnected):
    be(aliceCli)
    do('sync {inviter}',                expect=syncWhenNotConnected,
                                        mapper=faberMap)


def testAcceptUnSyncedInviteWhenNotConnected(be, do,
                                             faberInviteLoadedByAlice,
                                             acceptUnSyncedWhenNotConnected,
                                             faberMap):
    aliceCli = faberInviteLoadedByAlice
    be(aliceCli)
    do('accept invitation {inviter}',   expect=acceptUnSyncedWhenNotConnected,
                                        mapper=faberMap)

@pytest.fixture(scope="module")
def faberInviteSyncedWithoutEndpoint(be, do, aliceCli, faberMap,
                                     faberInviteLoadedByAlice, poolNodesStarted,
                                     connectedToTest,
                                     syncLinkOutWithoutEndpoint):
    be(aliceCli)

    do('connect test',                  within=3,
                                        expect=connectedToTest,
                                        mapper=faberMap)

    do('sync {inviter}',                within=2,
                                        expect=syncLinkOutWithoutEndpoint,
                                        mapper=faberMap)
    return aliceCli


def testSyncFaberInvite(faberInviteSyncedWithoutEndpoint):
    pass


def testShowSyncedInvite(be, do, faberInviteSyncedWithoutEndpoint, faberMap,
                         linkNotYetSynced, showSyncedLinkWithoutEndpointOut):
    aliceCLI = faberInviteSyncedWithoutEndpoint

    be(aliceCLI)

    do('show link {inviter}',           expect=showSyncedLinkWithoutEndpointOut,
                                        not_expect=linkNotYetSynced,
                                        mapper=faberMap)


@pytest.fixture(scope="module")
def faberWithEndpointAdded(be, do, faberAddedByPhil, faberMap, attrAddedOut):
    philCli = faberAddedByPhil
    be(philCli)
    # I had to give two open/close curly braces in raw data
    # to avoid issue in mapping
    do('send ATTRIB dest={target} raw={{"endpoint": "0.0.0.0:1212"}}',
                                        within=3,
                                        expect=attrAddedOut,
                                        mapper=faberMap)
    return philCli


def testEndpointAddedForFaber(faberWithEndpointAdded):
    pass


@pytest.fixture(scope="module")
def faberInviteSyncedWithEndpoint(be, do, faberMap,
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


def testAcceptNotExistsLink(be, do, aliceCli, linkNotExists, faberMap):
    be(aliceCli)
    do('accept invitation {inviter-not-exists}',
                                        expect=linkNotExists, mapper=faberMap)


@pytest.fixture(scope="module")
def faberAgentStarted(faberInviteLoadedByAlice):
    faberCli = faberInviteLoadedByAlice
    return FaberAgent(name="faber", client=faberCli.activeClient,
                      port=FABER_ENDPOINT_PORT)


# TODO: Below tests works fine individually, when run inside whole suite,
# then, it fails (seems, cli state doesn't get clear)
def testAcceptUnSyncedInviteWhenConnected(be, do, faberInviteLoadedByAlice,
                                          acceptUnSyncedWhenConnected,
                                          faberMap, connectedToTest,
                                          poolNodesStarted, faberAgentStarted):
    aliceCli = faberInviteLoadedByAlice
    be(aliceCli)
    if not aliceCli ._isConnectedToAnyEnv():
        do('connect test',              within=3,
                                        expect=connectedToTest,
                                        mapper=faberMap)

    do('accept invitation {inviter}',   within=3,
                                        expect=acceptUnSyncedWhenConnected,
                                        mapper=faberMap)


def testAcceptInvitationResponseWithInvalidSig(faberInviteSyncedWithEndpoint,
                                 faberCli):
    aliceCli = faberInviteSyncedWithEndpoint
    aliceSigner = aliceCli.activeWallet._getIdData(
        aliceCli.activeWallet.defaultId).signer
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
      }""".replace("<identifier>", faberCli.activeWallet.defaultId)

    acceptInviteResp = json.loads(msg)
    signature = aliceSigner.sign(acceptInviteResp)
    acceptInviteResp["signature"] = signature

    aliceCli._handleAcceptInviteResponse(acceptInviteResp)
    assert "Signature rejected" in aliceCli.lastCmdOutput


@pytest.fixture(scope="module")
def faberRespondedToAcceptInvite(faberInviteSyncedWithEndpoint,
                                 faberCli):
    aliceCli = faberInviteSyncedWithEndpoint
    faberSigner = faberCli.activeWallet._getIdData(
        faberCli.activeWallet.defaultId).signer
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
      }""".replace("<identifier>", faberCli.activeWallet.defaultId)

    acceptInviteResp = json.loads(msg)
    signature = faberSigner.sign(acceptInviteResp)
    acceptInviteResp["signature"] = signature

    aliceCli._handleAcceptInviteResponse(acceptInviteResp)
    assert "Signature accepted." in aliceCli.lastCmdOutput
    assert "Trust established." in aliceCli.lastCmdOutput
    assert "Identifier created in Sovrin." in aliceCli.lastCmdOutput
    assert "Available claims: Transcript" in aliceCli.lastCmdOutput
    return aliceCli


def testFaberRespondsToAcceptInvite(faberRespondedToAcceptInvite):
    pass


def testShowLinkAfterInviteAccept(be, do, faberMap, showAcceptedLinkOut,
                                  faberRespondedToAcceptInvite):
    aliceCli = faberRespondedToAcceptInvite

    be(aliceCli)

    do("show link {inviter}",           expect=showAcceptedLinkOut,
                                        not_expect="Link (not yet accepted)",
                                        mapper=faberMap)