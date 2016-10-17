import uuid

import pytest
import time
from plenum.common.types import f

from plenum.common.txn import TYPE, NONCE, IDENTIFIER, NAME, VERSION
from plenum.test.eventually import eventually
from sovrin.agent.msg_types import ACCEPT_INVITE, AVAIL_CLAIM_LIST
from sovrin.client.wallet.claim_def import ClaimDef, IssuerPubKey
from sovrin.client.wallet.link import Link, constant
from sovrin.common.exceptions import InvalidLinkException
from sovrin.common.txn import ENDPOINT, ATTR_NAMES
from sovrin.test.cli.helper import getFileLines


# FABER_ENDPOINT_PORT = 1212
from anoncreds.protocol.cred_def_secret_key import CredDefSecretKey
from anoncreds.protocol.issuer_secret_key import IssuerSecretKey
from anoncreds.protocol.types import AttribDef, AttribType


def getSampleLinkInvitation():
    return {
        "link-invitation": {
            "name": "Acme Corp",
            "identifier": "7YD5NKn3P4wVJLesAmA1rr7sLPqW9mR1nhFdKD518k21",
            "nonce": "57fbf9dc8c8e6acde33de98c6d747b28c",
            "endpoint": "127.0.0.1:1213"
        },
        "claim-requests": [{
            "name": "Job-Application",
            "version": "0.2",
            "attributes": {
                "first_name": "string",
                "last_name": "string",
                "phone_number": "string",
                "degree": "string",
                "status": "string",
                "ssn": "string"
            }
        }],
        "sig": "KDkI4XUePwEu1K01u0DpDsbeEfBnnBfwuw8e4DEPK+MdYXv"
               "VsXdSmBJ7yEfQBm8bSJuj6/4CRNI39fFul6DcDA=="
    }


def prompt_is(prompt):
    def x(cli):
        assert cli.currPromptText == prompt
    return x


@pytest.yield_fixture(scope="module")
def faberCLI(CliBuilder):
    yield from CliBuilder("faber")


@pytest.yield_fixture(scope="module")
def acmeCLI(CliBuilder):
    yield from CliBuilder("acme")


@pytest.yield_fixture(scope="module")
def thriftCLI(CliBuilder):
    yield from CliBuilder("thrift")


@pytest.fixture(scope="module")
def poolNodesStarted(be, do, poolCLI):
    be(poolCLI)

    do('new node all',              within=6,
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

    do('prompt FABER',              expect=prompt_is('FABER'))

    do('new keyring Faber',         expect=['New keyring Faber created',
                                            'Active keyring set to "Faber"'])
    seed = 'Faber000000000000000000000000000'
    idr = 'FuN98eH2eZybECWkofW6A9BKJxxnTatBCopfUiNxo6ZB'

    do('new key with seed ' + seed, expect=['Key created in keyring Faber',
                                           'Identifier for key is ' + idr,
                                           'Current identifier set to ' + idr])
    return faberCLI


@pytest.fixture(scope="module")
def acmeCli(be, do, acmeCLI):
    be(acmeCLI)

    do('prompt Acme',               expect=prompt_is('Acme'))

    do('new keyring Acme',          expect=['New keyring Acme created',
                                            'Active keyring set to "Acme"'])
    seed = 'Acme0000000000000000000000000000'
    idr = '7YD5NKn3P4wVJLesAmA1rr7sLPqW9mR1nhFdKD518k21'

    do('new key with seed ' + seed, expect=['Key created in keyring Acme',
                                            'Identifier for key is ' + idr,
                                            'Current identifier set to ' + idr])
    return acmeCLI


@pytest.fixture(scope="module")
def thriftCli(be, do, thriftCLI):
    be(thriftCLI)

    do('prompt Thrift',               expect=prompt_is('Thrift'))

    do('new keyring Thrift',          expect=['New keyring Thrift created',
                                              'Active keyring set to "Thrift"'])
    seed = 'Thrift00000000000000000000000000'
    idr = '9jegUr9vAMqoqQQUEAiCBYNQDnUbTktQY9nNspxfasZW'

    do('new key with seed ' + seed, expect=['Key created in keyring Thrift',
                                            'Identifier for key is ' + idr,
                                            'Current identifier set to ' + idr])
    return acmeCLI


@pytest.fixture(scope="module")
def philCli(be, do, philCLI):
    be(philCLI)
    do('prompt Phil',               expect=prompt_is('Phil'))

    do('new keyring Phil',          expect=['New keyring Phil created',
                                            'Active keyring set to "Phil"'])

    mapper = {
        'seed': '11111111111111111111111111111111',
        'idr': '5rArie7XKukPCaEwq5XGQJnM9Fc5aZE3M9HAPVfMU2xC'}
    do('new key with seed {seed}',  expect=['Key created in keyring Phil',
                                            'Identifier for key is {idr}',
                                            'Current identifier set to {idr}'],
       mapper=mapper)

    return philCLI


@pytest.fixture(scope="module")
def faberAddedByPhil(be, do, poolNodesStarted, philCli, connectedToTest,
                     nymAddedOut, faberMap):
    be(philCli)
    if not philCli._isConnectedToAnyEnv():
        do('connect test',          within=3,
                                    expect=connectedToTest)

    do('send NYM dest={target} role=SPONSOR',
                                    within=3,
                                    expect=nymAddedOut, mapper=faberMap)
    return philCli


@pytest.fixture(scope="module")
def acmeAddedByPhil(be, do, poolNodesStarted, philCli, connectedToTest,
                     nymAddedOut, acmeMap):
    be(philCli)
    if not philCli._isConnectedToAnyEnv():
        do('connect test',          within=3,
                                    expect=connectedToTest)

    do('send NYM dest={target} role=SPONSOR',
                                    within=3,
                                    expect=nymAddedOut, mapper=acmeMap)
    return philCli


@pytest.fixture(scope="module")
def thriftAddedByPhil(be, do, poolNodesStarted, philCli, connectedToTest,
                     nymAddedOut, thriftMap):
    be(philCli)
    if not philCli._isConnectedToAnyEnv():
        do('connect test',          within=3,
                                    expect=connectedToTest)

    do('send NYM dest={target} role=SPONSOR',
                                    within=3,
                                    expect=nymAddedOut, mapper=thriftMap)
    return philCli


@pytest.fixture(scope="module")
def faberWithEndpointAdded(be, do, philCli, faberAddedByPhil,
                           faberMap, attrAddedOut):

    be(philCli)
    do('send ATTRIB dest={target} raw={endpointAttr}',
                                    within=3,
                                    expect=attrAddedOut,
                                    mapper=faberMap)
    return philCli


@pytest.fixture(scope="module")
def acmeWithEndpointAdded(be, do, philCli, acmeAddedByPhil,
                           acmeMap, attrAddedOut):

    be(philCli)
    do('send ATTRIB dest={target} raw={endpointAttr}',
                                    within=3,
                                    expect=attrAddedOut,
                                    mapper=acmeMap)
    return philCli


@pytest.fixture(scope="module")
def thriftWithEndpointAdded(be, do, philCli, thriftAddedByPhil,
                            thriftMap, attrAddedOut):

    be(philCli)
    do('send ATTRIB dest={target} raw={endpointAttr}',
                                    within=3,
                                    expect=attrAddedOut,
                                    mapper=thriftMap)
    return philCli


def connectIfNotAlreadyConnected(do, expectMsgs, userCli, userMap):
    # TODO: Shouldn't this be testing the cli command `status`?
    if not userCli._isConnectedToAnyEnv():
        do('connect test',          within=3,
                                    expect=expectMsgs,
                                    mapper=userMap)


def checkWalletStates(userCli,
                      totalLinks,
                      totalAvailableClaims,
                      totalCredDefs,
                      totalClaimsRcvd,
                      within=None):

    def check():
        assert totalLinks == len(userCli.activeWallet._links)

        tac = 0
        for li in userCli.activeWallet._links.values():
            tac += len(li.availableClaims)
        assert totalAvailableClaims == tac

        assert totalCredDefs == len(userCli.activeWallet._claimDefs)

        assert totalClaimsRcvd == \
               len(userCli.activeWallet.attributesFrom.keys())

    if within:
        userCli.looper.run(eventually(check, timeout=within))
    else:
        check()


@pytest.fixture(scope="module")
def aliceCli(be, do, aliceCLI, newKeyringOut, aliceMap):
    be(aliceCLI)

    do('prompt ALICE',              expect=prompt_is('ALICE'))

    do('new keyring Alice',         expect=newKeyringOut, mapper=aliceMap)
    return aliceCLI


def testNotConnected(be, do, aliceCli, notConnectedStatus):
    be(aliceCli)
    do('status',                    expect=notConnectedStatus)


def testShowInviteNotExists(be, do, aliceCli, fileNotExists, faberMap):
    checkWalletStates(aliceCli, totalLinks=0, totalAvailableClaims=0,
                      totalCredDefs=0, totalClaimsRcvd=0)
    be(aliceCli)
    do('show {invite-not-exists}',  expect=fileNotExists, mapper=faberMap)


def testShowInviteWithDirPath(be, do, aliceCli, fileNotExists, faberMap):
    checkWalletStates(aliceCli, totalLinks=0, totalAvailableClaims=0,
                      totalCredDefs=0, totalClaimsRcvd=0)
    be(aliceCli)
    do('show sample',  expect=fileNotExists, mapper=faberMap)


def testLoadLinkInviteWithoutSig():
    li = getSampleLinkInvitation()
    del li["sig"]
    with pytest.raises(InvalidLinkException) as excinfo:
        Link.validate(li)
    assert "Field not found in given input: sig" in str(excinfo.value)


def testShowFaberInvite(be, do, aliceCli, faberMap):
    be(aliceCli)
    inviteContents = getFileLines(faberMap.get("invite"))

    do('show {invite}',             expect=inviteContents,
                                    mapper=faberMap)


def testLoadInviteNotExists(be, do, aliceCli, fileNotExists, faberMap):
    be(aliceCli)
    do('load {invite-not-exists}',  expect=fileNotExists, mapper=faberMap)


@pytest.fixture(scope="module")
def faberInviteLoadedByAlice(be, do, aliceCli, loadInviteOut, faberMap):
    checkWalletStates(aliceCli, totalLinks=0, totalAvailableClaims=0,
                      totalCredDefs=0, totalClaimsRcvd=0)
    be(aliceCli)
    do('load {invite}',             expect=loadInviteOut, mapper=faberMap)
    checkWalletStates(aliceCli, totalLinks=1, totalAvailableClaims=0,
                      totalCredDefs=0, totalClaimsRcvd=0)
    return aliceCli


def testLoadFaberInvite(faberInviteLoadedByAlice):
    pass


def testShowLinkNotExists(be, do, aliceCli, linkNotExists, faberMap):
    be(aliceCli)
    do('show link {inviter-not-exists}',
                                    expect=linkNotExists,
                                    mapper=faberMap)


def testShowFaberLink(be, do, aliceCli, faberInviteLoadedByAlice,
                       showUnSyncedLinkOut, faberMap):
    be(aliceCli)
    do('show link {inviter}',       expect=showUnSyncedLinkOut,
                                    mapper=faberMap)


def testSyncLinkNotExists(be, do, aliceCli, linkNotExists, faberMap):
    be(aliceCli)
    do('sync {inviter-not-exists}', expect=linkNotExists, mapper=faberMap)


def testSyncFaberWhenNotConnected(be, do, aliceCli, faberMap,
                                        faberInviteLoadedByAlice,
                                        syncWhenNotConnected):
    be(aliceCli)
    do('sync {inviter}',            expect=syncWhenNotConnected,
                                    mapper=faberMap)


def testAcceptUnSyncedFaberInviteWhenNotConnected(be, do, aliceCli,
                                             faberInviteLoadedByAlice,
                                             acceptUnSyncedWhenNotConnected,
                                             faberMap):
    be(aliceCli)
    do('accept invitation from {inviter}',
                                    expect=acceptUnSyncedWhenNotConnected,
                                    mapper=faberMap)


def testAcceptUnSyncedFaberInvite(be, do, aliceCli, faberInviteLoadedByAlice,
                                  acceptUnSyncedWithoutEndpointWhenConnected,
                                  faberMap, connectedToTest,
                                  faberAddedByPhil,
                                  faberIsRunning,
                                  poolNodesStarted):
    be(aliceCli)
    connectIfNotAlreadyConnected(do, connectedToTest, aliceCli, faberMap)

    checkWalletStates(aliceCli, totalLinks=1, totalAvailableClaims=0,
                      totalCredDefs=0, totalClaimsRcvd=0)
    do('accept invitation from {inviter}',
                                    within=3,
                                    expect=acceptUnSyncedWithoutEndpointWhenConnected,
                                    mapper=faberMap)
    checkWalletStates(aliceCli, totalLinks=1, totalAvailableClaims=0,
                      totalCredDefs=0, totalClaimsRcvd=0)


@pytest.fixture(scope="module")
def faberInviteSyncedWithoutEndpoint(be, do, aliceCli, faberMap,
                                     faberInviteLoadedByAlice, poolNodesStarted,
                                     connectedToTest,
                                     faberAddedByPhil,
                                     faberIsRunning,
                                     linkNotYetSynced,
                                     syncLinkOutWithoutEndpoint):
    be(aliceCli)
    connectIfNotAlreadyConnected(do, connectedToTest, aliceCli, faberMap)

    do('sync {inviter}',            within=2,
                                    expect=syncLinkOutWithoutEndpoint,
                                    mapper=faberMap)
    return aliceCli


def testSyncFaberInviteWithoutEndpoint(faberInviteSyncedWithoutEndpoint):
    pass


def testShowSyncedFaberInvite(be, do, aliceCli, faberMap, linkNotYetSynced,
                              faberInviteSyncedWithoutEndpoint,
                              showSyncedLinkWithoutEndpointOut):

    be(aliceCli)

    do('show link {inviter}',       within=4,
                                    expect=showSyncedLinkWithoutEndpointOut,
                                    # TODO, need to come back to not_expect
                                    # not_expect=linkNotYetSynced,
                                    mapper=faberMap)


def testEndpointAddedForFaber(faberWithEndpointAdded):
    pass


def syncInvite(be, do, userCli, expectedMsgs, mapping):
    be(userCli)

    do('sync {inviter}',            within=2,
                                    expect=expectedMsgs,
                                    mapper=mapping)


@pytest.fixture(scope="module")
def faberInviteSyncedWithEndpoint(be, do, faberMap, aliceCLI,
                                  faberInviteSyncedWithoutEndpoint,
                                  faberWithEndpointAdded,
                                  syncLinkOutWithEndpoint,
                                  poolNodesStarted):
    syncInvite(be, do, aliceCLI, syncLinkOutWithEndpoint, faberMap)
    return aliceCLI


def testSyncFaberInvite(faberInviteSyncedWithEndpoint):
    pass


def testShowSyncedFaberInviteWithEndpoint(be, do, aliceCLI,
                                          faberInviteSyncedWithEndpoint,
                                     showSyncedLinkWithEndpointOut, faberMap):
    be(aliceCLI)
    do('show link {inviter}',       expect=showSyncedLinkWithEndpointOut,
                                    mapper=faberMap)


def testAcceptNotExistsLink(be, do, aliceCli, linkNotExists, faberMap):
    be(aliceCli)
    do('accept invitation from {inviter-not-exists}',
                                    expect=linkNotExists, mapper=faberMap)


def getSignedRespMsg(msg, signer):
    signature = signer.sign(msg)
    msg["signature"] = signature
    return msg


def acceptInvitation(be, do, userCli, agentMap, expect):
    be(userCli)
    do("accept invitation from {inviter}",
                                    within=15,
                                    mapper=agentMap,
                                    expect=expect,
                                    not_expect=[
                                        "Observer threw an exception",
                                        "Identifier is not yet written to Sovrin"]
                                    )


@pytest.fixture(scope="module")
def aliceAcceptedFaberInvitation(be, do, aliceCli, faberMap,
                                 faberAddedByPhil,
                                 syncedInviteAcceptedWithClaimsOut,
                                 faberLinkAdded, faberIsRunning,
                                 faberInviteSyncedWithEndpoint):
    checkWalletStates(aliceCli, totalLinks=1, totalAvailableClaims=0,
                      totalCredDefs=0, totalClaimsRcvd=0)
    acceptInvitation(be, do, aliceCli, faberMap,
                     syncedInviteAcceptedWithClaimsOut)
    checkWalletStates(aliceCli, totalLinks=1, totalAvailableClaims=1,
                      totalCredDefs=1, totalClaimsRcvd=0)
    return aliceCli


def testAliceAcceptFaberInvitationFirstTime(aliceAcceptedFaberInvitation):
    pass


def testAliceAcceptFaberInvitationAgain(be, do, aliceCli, faberMap,
                                        unsycedAlreadyAcceptedInviteAcceptedOut,
                                        aliceAcceptedFaberInvitation):

    li = aliceCli.activeWallet.getLinkInvitationByTarget(faberMap['target'])
    li.linkStatus = None
    be(aliceCli)
    checkWalletStates(aliceCli, totalLinks=1, totalAvailableClaims=1,
                      totalCredDefs=1, totalClaimsRcvd=0)
    acceptInvitation(be, do, aliceCli, faberMap,
                     unsycedAlreadyAcceptedInviteAcceptedOut)
    checkWalletStates(aliceCli, totalLinks=1, totalAvailableClaims=1,
                      totalCredDefs=1, totalClaimsRcvd=0)
    li.linkStatus = constant.LINK_STATUS_ACCEPTED


# TODO: Write tests which sends request with invalid signature
# TODO: Write tests which receives response with invalid signature

def testShowFaberLinkAfterInviteAccept(be, do, aliceCli, faberMap,
                                       showAcceptedLinkOut,
                                       aliceAcceptedFaberInvitation):
    be(aliceCli)

    do("show link {inviter}",       expect=showAcceptedLinkOut,
                                    # not_expect="Link (not yet accepted)",
                                    mapper=faberMap)


def testShowClaimNotExists(be, do, aliceCli, faberMap, showClaimNotFoundOut,
                                   aliceAcceptedFaberInvitation):
    be(aliceCli)

    do("show claim claim-to-show-not-exists",
                                    expect=showClaimNotFoundOut,
                                    mapper=faberMap)


def testShowTranscriptClaim(be, do, aliceCli, transcriptClaimMap,
                            showTranscriptClaimOut,
                            aliceAcceptedFaberInvitation):

    be(aliceCli)

    do("show claim {name}",
                                    expect=showTranscriptClaimOut,
                                    mapper=transcriptClaimMap)


def testReqClaimNotExists(be, do, aliceCli, faberMap, showClaimNotFoundOut,
                                   aliceAcceptedFaberInvitation):
    be(aliceCli)

    do("request claim claim-to-req-not-exists",
                                    expect=showClaimNotFoundOut,
                                    mapper=faberMap)


@pytest.fixture(scope="module")
def aliceRequestedTranscriptClaim(be, do, aliceCli, transcriptClaimMap,
                                       reqClaimOut,
                                       faberIsRunning,
                                       aliceAcceptedFaberInvitation):
    be(aliceCli)
    checkWalletStates(aliceCli, totalLinks=1, totalAvailableClaims=1,
                      totalCredDefs=1, totalClaimsRcvd=0)
    do("request claim {name}",      within=5,
                                    expect=reqClaimOut,
                                    mapper=transcriptClaimMap)

    checkWalletStates(aliceCli, totalLinks=1, totalAvailableClaims=1,
                      totalCredDefs=1, totalClaimsRcvd=1, within=2)


def testAliceReqClaim(aliceRequestedTranscriptClaim):
    pass


def testReqTranscriptClaimWithClaimDefNotInWallet(be, do, aliceCli,
                    transcriptClaimMap, reqClaimOut1, faberIsRunning,
                                                  aliceAcceptedFaberInvitation):
    be(aliceCli)
    inviter = transcriptClaimMap["inviter"]
    links = aliceCli.activeWallet.getMatchingLinks(inviter)
    assert len(links) == 1
    faberId = links[0].remoteIdentifier
    name, version = transcriptClaimMap["name"], transcriptClaimMap["version"]
    aliceCli.activeWallet._claimDefs.pop((name, version, faberId))
    do("request claim {name}",      within=5,
                                    expect=reqClaimOut1,
                                    mapper=transcriptClaimMap)


def testShowFaberClaimPostReqClaim(be, do, aliceCli,
                                   aliceRequestedTranscriptClaim,
                                   transcriptClaimValueMap,
                                   rcvdTranscriptClaimOut):
    be(aliceCli)
    do("show claim {name}",
                                    expect=rcvdTranscriptClaimOut,
                                    mapper=transcriptClaimValueMap)


def testShowAcmeInvite(be, do, aliceCli, acmeMap):
    be(aliceCli)
    inviteContents = getFileLines(acmeMap.get("invite"))

    do('show {invite}',             expect=inviteContents,
                                    mapper=acmeMap)


@pytest.fixture(scope="module")
def acmeInviteLoadedByAlice(be, do, aliceCli, loadInviteOut, acmeMap):
    checkWalletStates(aliceCli, totalLinks=1, totalAvailableClaims=1,
                      totalCredDefs=1, totalClaimsRcvd=1)
    be(aliceCli)
    do('load {invite}',             expect=loadInviteOut, mapper=acmeMap)
    link = aliceCli.activeWallet.getLinkInvitation(acmeMap.get("inviter"))
    link.remoteEndPoint = acmeMap.get(ENDPOINT)

    checkWalletStates(aliceCli, totalLinks=2, totalAvailableClaims=1,
                      totalCredDefs=1, totalClaimsRcvd=1)

    return aliceCli


def testLoadAcmeInvite(acmeInviteLoadedByAlice):
    pass


def testShowAcmeLink(be, do, aliceCli, acmeInviteLoadedByAlice,
                       showUnSyncedLinkOut, showLinkWithClaimReqOut, acmeMap):
    showUnSyncedLinkWithClaimReqs = \
        showUnSyncedLinkOut + showLinkWithClaimReqOut
    be(aliceCli)
    do('show link {inviter}',       expect=showUnSyncedLinkWithClaimReqs,
                                    mapper=acmeMap)


@pytest.fixture(scope="module")
def aliceAcceptedAcmeJobInvitation(aliceCli, be, do,
                                   unsycedAcceptedInviteWithoutClaimOut,
                                   aliceRequestedTranscriptClaim,
                                   acmeInviteLoadedByAlice, acmeAddedByPhil,
                                   acmeIsRunning, acmeMap, acmeLinkAdded,
                                   acmeWithEndpointAdded):
    checkWalletStates(aliceCli, totalLinks=2, totalAvailableClaims=1,
                      totalCredDefs=1, totalClaimsRcvd=1)
    be(aliceCli)
    acceptInvitation(be, do, aliceCli, acmeMap,
                     unsycedAcceptedInviteWithoutClaimOut)

    checkWalletStates(aliceCli, totalLinks=2, totalAvailableClaims=1,
                      totalCredDefs=1, totalClaimsRcvd=1)
    return aliceCli


def testAliceAcceptAcmeJobInvitation(aliceAcceptedAcmeJobInvitation):
    pass


def testSetAttrWithoutContext(be, do, aliceCli):
    be(aliceCli)
    do("set first_name to Alice",   expect=[
                                            "No context, "
                                            "use below command to "
                                            "set the context"])


def testShowAcmeLinkAfterInviteAccept(be, do, aliceCli, acmeMap,
                                      aliceAcceptedAcmeJobInvitation,
                                      showAcceptedLinkWithoutAvailableClaimsOut):

    be(aliceCli)

    do("show link {inviter}",       expect=showAcceptedLinkWithoutAvailableClaimsOut,
                                    not_expect="Link (not yet accepted)",
                                    mapper=acmeMap)


def testShowClaimReqNotExists(be, do, aliceCli, acmeMap, claimReqNotExists):
    be(aliceCli)
    do("show claim request claim-req-to-show-not-exists",
                                    expect=claimReqNotExists,
                                    mapper=acmeMap)


def claimReqShown(be, do, userCli, agentMap,
                                   claimReqOut,
                                   claimReqMap,
                                   claimAttrValueMap):
    be(userCli)

    mapping = {
        "set-attr-first_name": "",
        "set-attr-last_name": "",
        "set-attr-phone_number": ""
    }
    mapping.update(agentMap)
    mapping.update(claimReqMap)
    mapping.update(claimAttrValueMap)
    do("show claim request {claim-req-to-show}",
                                    expect=claimReqOut,
                                    mapper=mapping)


def testShowJobAppClaimReqWithShortName(be, do, aliceCli, acmeMap,
                                   showJobAppClaimReqOut,
                                   jobApplicationClaimReqMap,
                                   transcriptClaimAttrValueMap,
                                   aliceAcceptedAcmeJobInvitation):
    newAcmeMap = {}
    newAcmeMap.update(acmeMap)
    newAcmeMap["claim-req-to-show"] = "Job"

    claimReqShown(be, do, aliceCli, newAcmeMap,
                                   showJobAppClaimReqOut,
                                   jobApplicationClaimReqMap,
                                   transcriptClaimAttrValueMap)


def testShowJobAppilcationClaimReq(be, do, aliceCli, acmeMap,
                                   showJobAppClaimReqOut,
                                   jobApplicationClaimReqMap,
                                   transcriptClaimAttrValueMap,
                                   aliceAcceptedAcmeJobInvitation):
    claimReqShown(be, do, aliceCli, acmeMap,
                                   showJobAppClaimReqOut,
                                   jobApplicationClaimReqMap,
                                   transcriptClaimAttrValueMap)


@pytest.fixture(scope="module")
def aliceSelfAttestsAttributes(be, do, aliceCli, acmeMap,
                                               showJobAppClaimReqOut,
                                               jobApplicationClaimReqMap,
                                               transcriptClaimAttrValueMap,
                                               aliceAcceptedAcmeJobInvitation):
    be(aliceCli)

    mapping = {
        "set-attr-first_name": "",
        "set-attr-last_name": "",
        "set-attr-phone_number": ""
    }
    mapping.update(acmeMap)
    mapping.update(jobApplicationClaimReqMap)
    mapping.update(transcriptClaimAttrValueMap)
    do("show claim request {claim-req-to-show}",
       expect=showJobAppClaimReqOut,
       mapper=mapping)
    do("set first_name to Alice")
    do("set last_name to Garcia")
    do("set phone_number to 123-555-1212")
    mapping.update({
        "set-attr-first_name": "Alice",
        "set-attr-last_name": "Garcia",
        "set-attr-phone_number": "123-555-1212"
    })
    return mapping


def testShowJobApplicationClaimReqAfterSetAttr(be, do, aliceCli,
                                               showJobAppClaimReqOut,
                                               aliceSelfAttestsAttributes):
    be(aliceCli)
    do("show claim request {claim-req-to-show}",
                                    expect=showJobAppClaimReqOut,
                                    mapper=aliceSelfAttestsAttributes)


def testInvalidSigErrorResponse(be, do, aliceCli, faberMap,
                                faberIsRunning,
                                faberInviteSyncedWithoutEndpoint):

    msg = {
        TYPE: ACCEPT_INVITE,
        IDENTIFIER: faberMap['target'],
        NONCE: "unknown"
    }
    signature = aliceCli.activeWallet.signMsg(msg,
                                              aliceCli.activeWallet.defaultId)
    msg[f.SIG.nm] = signature
    link = aliceCli.activeWallet.getLink(faberMap['inviter'], required=True)
    aliceCli.sendToAgent(msg, link)

    be(aliceCli)
    do(None,                        within=3,
                                    expect=["Signature rejected.".
                                                format(msg)])


def testLinkNotFoundErrorResponse(be, do, aliceCli, faberMap,
                      faberInviteSyncedWithoutEndpoint):

    msg = {
        TYPE: ACCEPT_INVITE,
        IDENTIFIER: aliceCli.activeWallet.defaultId,
        NONCE: "unknown"
    }
    signature = aliceCli.activeWallet.signMsg(msg,
                                              aliceCli.activeWallet.defaultId)
    msg[f.SIG.nm] = signature
    link = aliceCli.activeWallet.getLink(faberMap['inviter'], required=True)
    aliceCli.sendToAgent(msg, link)

    be(aliceCli)
    do(None, within=3,
             expect=["Nonce not found".format(msg)])


def sendClaim(be, do, userCli, agentMap, newAvailableClaims, extraMsgs=None):
    be(userCli)

    expectMsgs = [
        "Your claim {claim-req-to-match} "
        "{claim-ver-req-to-show} has been "
        "received and verified"
    ]
    if extraMsgs:
        expectMsgs.extend(extraMsgs)
    mapping = {}
    mapping.update(agentMap)
    if newAvailableClaims:
        mapping['new-available-claims'] = newAvailableClaims
        expectMsgs.append("Available claims: {new-available-claims}")

    do("send claim {claim-req-to-match} to {inviter}",
                                    within=7,
                                    expect=expectMsgs,
                                    mapper=mapping)


def testReqUnavailableClaim(be, do, aliceCli,
                            acmeMap,
                            reqClaimOut1,
                            acmeIsRunning,
                            aliceAcceptedAcmeJobInvitation):

    acme, _ = acmeIsRunning
    be(aliceCli)

    checkWalletStates(aliceCli, totalLinks=2, totalAvailableClaims=1,
                      totalCredDefs=1, totalClaimsRcvd=1)

    link = aliceCli.activeWallet._links[acmeMap.get('inviter')]
    oldAvailableClaims = []
    oldCredDefs = {}
    for ac in link.availableClaims:
        oldAvailableClaims.append(ac)

    for cd in aliceCli.activeWallet._claimDefs.values():
        oldCredDefs[cd.key] = cd

    newAvailableClaims = acme.getJobCertAvailableClaimList()

    def dummyPostCredDef(li, nac):
        pass

    aliceCli.agent._processNewAvailableClaimsData(
        link, newAvailableClaims, dummyPostCredDef)

    time.sleep(3)

    do("request claim Job-Certificate",
       within=7,
       expect=["This claim is not yet available"])

    link.availableClaims = oldAvailableClaims
    aliceCli.activeWallet._claimDefs = oldCredDefs
    checkWalletStates(aliceCli, totalLinks=2, totalAvailableClaims=1,
                      totalCredDefs=1, totalClaimsRcvd=1)


@pytest.fixture(scope="module")
def jobApplicationClaimSent(be, do, aliceCli, acmeMap,
                                    aliceAcceptedAcmeJobInvitation,
                                  aliceRequestedTranscriptClaim,
                                  aliceSelfAttestsAttributes):

    checkWalletStates(aliceCli, totalLinks=2, totalAvailableClaims=1,
                      totalCredDefs=1, totalClaimsRcvd=1)
    sendClaim(be, do, aliceCli, acmeMap, "Job-Certificate")

    checkWalletStates(aliceCli, totalLinks=2, totalAvailableClaims=2,
                      totalCredDefs=2, totalClaimsRcvd=1)


def testAliceSendClaimProofToAcme(jobApplicationClaimSent):
    pass


# TODO: Need to uncomment below tests once above testAliceSendClaimProofToAcme
# test works correctly all the time and also we start supporting
# building and sending claim proofs from more than one claim

def testShowAcmeLinkAfterClaimSent(be, do, aliceCli, acmeMap,
                                   jobApplicationClaimSent,
                                   showAcceptedLinkWithAvailableClaimsOut):

    be(aliceCli)
    mapping = {}
    mapping.update(acmeMap)
    mapping["claims"] = "Job-Certificate"

    acmeMap.update(acmeMap)
    do("show link {inviter}",       expect=showAcceptedLinkWithAvailableClaimsOut,
                                    mapper=mapping)


def testShowJobCertClaim(be, do, aliceCli, jobCertificateClaimMap,
                         showJobCertClaimOut,
                         jobApplicationClaimSent):

    be(aliceCli)
    checkWalletStates(aliceCli, totalLinks=2, totalAvailableClaims=2,
                      totalCredDefs=2, totalClaimsRcvd=1)
    do("show claim {name}",
                                    within=2,
                                    expect=showJobCertClaimOut,
                                    mapper=jobCertificateClaimMap)

    checkWalletStates(aliceCli, totalLinks=2, totalAvailableClaims=2,
                      totalCredDefs=2, totalClaimsRcvd=1)


@pytest.fixture(scope="module")
def jobCertClaimRequested(be, do, aliceCli,
                        jobCertificateClaimMap, reqClaimOut1, acmeIsRunning,
                        jobApplicationClaimSent):

    def removeClaimDef():
        inviter = jobCertificateClaimMap["inviter"]
        links = aliceCli.activeWallet.getMatchingLinks(inviter)
        assert len(links) == 1
        faberId = links[0].remoteIdentifier
        name, version = jobCertificateClaimMap["name"], \
                        jobCertificateClaimMap["version"]
        aliceCli.activeWallet._claimDefs.pop((name, version, faberId))

    # Removing claim def to check if it fetches the claim def again or not
    removeClaimDef()

    be(aliceCli)

    checkWalletStates(aliceCli, totalLinks=2, totalAvailableClaims=2,
                      totalCredDefs=1, totalClaimsRcvd=1)

    do("request claim {name}",      within=7,
                                    expect=reqClaimOut1,
                                    mapper=jobCertificateClaimMap)
    checkWalletStates(aliceCli, totalLinks=2, totalAvailableClaims=2,
                      totalCredDefs=2, totalClaimsRcvd=2)


def testReqJobCertClaim(jobCertClaimRequested):
    pass


def testShowAcmeClaimPostReqClaim(be, do, aliceCli,
                                  jobCertClaimRequested,
                                  jobCertificateClaimValueMap,
                                  rcvdJobCertClaimOut):
    be(aliceCli)
    do("show claim {name}",
                                    expect=rcvdJobCertClaimOut,
                                    mapper=jobCertificateClaimValueMap)


@pytest.fixture(scope="module")
def thriftInviteLoadedByAlice(be, do, aliceCli, loadInviteOut, thriftMap,
                              jobCertClaimRequested,
                              thriftAddedByPhil,
                              thriftWithEndpointAdded):
    be(aliceCli)
    checkWalletStates(aliceCli, totalLinks=2, totalAvailableClaims=2,
                      totalCredDefs=2, totalClaimsRcvd=2, within=2)

    do('load {invite}',             expect=loadInviteOut, mapper=thriftMap)

    checkWalletStates(aliceCli, totalLinks=3, totalAvailableClaims=2,
                      totalCredDefs=2, totalClaimsRcvd=2)
    return aliceCli


def testAliceLoadedThriftLoanApplication(thriftInviteLoadedByAlice):
    pass


@pytest.fixture(scope="module")
def aliceAcceptedThriftLoanApplication(be, do, aliceCli, thriftMap,
                                       connectedToTest,
                                       thriftIsRunning,
                                       thriftInviteLoadedByAlice,
                                       syncedInviteAcceptedOutWithoutClaims):
    checkWalletStates(aliceCli, totalLinks=3, totalAvailableClaims=2,
                      totalCredDefs=2, totalClaimsRcvd=2, within=2)

    connectIfNotAlreadyConnected(do, connectedToTest, aliceCli, thriftMap)

    acceptInvitation(be, do, aliceCli, thriftMap,
                     syncedInviteAcceptedOutWithoutClaims)

    checkWalletStates(aliceCli, totalLinks=3, totalAvailableClaims=2,
                      totalCredDefs=2, totalClaimsRcvd=2)
    return aliceCli


def testAliceAcceptsThriftLoanApplication(aliceAcceptedThriftLoanApplication):
    pass


@pytest.fixture(scope="module")
def bankBasicClaimSent(be, do, aliceCli, thriftMap,
                       aliceAcceptedThriftLoanApplication):
    mapping = {}
    mapping.update(thriftMap)
    mapping["claim-req-to-match"] = "Loan-Application-Basic"
    checkWalletStates(aliceCli, totalLinks=3, totalAvailableClaims=2,
                      totalCredDefs=2, totalClaimsRcvd=2)
    extraMsgs = ["Loan eligibility criteria satisfied, "
                 "please send another claim 'Loan-Application-KYC'"]
    sendClaim(be, do, aliceCli, mapping, None, extraMsgs)
    checkWalletStates(aliceCli, totalLinks=3, totalAvailableClaims=2,
                      totalCredDefs=2, totalClaimsRcvd=2)


def testAliceSendBankBasicClaim(bankBasicClaimSent):
    pass


@pytest.fixture(scope="module")
def bankKYCClaimSent(be, do, aliceCli, thriftMap,
                     bankBasicClaimSent):
    mapping = {}
    mapping.update(thriftMap)
    mapping["claim-req-to-match"] = "Loan-Application-KYC"
    checkWalletStates(aliceCli, totalLinks=3, totalAvailableClaims=2,
                      totalCredDefs=2, totalClaimsRcvd=2)
    sendClaim(be, do, aliceCli, mapping, None)
    checkWalletStates(aliceCli, totalLinks=3, totalAvailableClaims=2,
                      totalCredDefs=2, totalClaimsRcvd=2)


def testAliceSendBankKYCClaim(bankKYCClaimSent):
    pass
