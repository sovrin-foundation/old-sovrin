import uuid

import pytest
from plenum.common.types import f

from plenum.common.txn import TYPE, NONCE, IDENTIFIER, NAME, VERSION
from plenum.test.eventually import eventually
from sovrin.agent.agent import WalletedAgent
from sovrin.agent.msg_types import ACCEPT_INVITE
from sovrin.client.wallet.claim_def import ClaimDef, IssuerPubKey
from sovrin.client.wallet.link import Link
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
            "identifier": "YSTHvR/sxdu41ig9mcqMq/DI5USQMVU4kpa6anJhot4=",
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
    idr = '3W2465HP3OUPGkiNlTMl2iZ+NiMZegfUFIsl8378KH4='

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
    idr = 'YSTHvR/sxdu41ig9mcqMq/DI5USQMVU4kpa6anJhot4='

    do('new key with seed ' + seed, expect=['Key created in keyring Acme',
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
        'idr': 'SAdaWX5yGhVuLgeZ3lzAxTJNxufq8c3UYlCGjsUyFd0='}
    do('new key with seed {seed}',  expect=['Key created in keyring Phil',
                                            'Identifier for key is {idr}',
                                            'Current identifier set to {idr}'],
       mapper=mapper)

    return philCLI


@pytest.fixture(scope="module")
def faberAddedByPhil(be, do, poolNodesStarted, philCli, connectedToTest,
                     nymAddedOut, faberMap):
    be(philCli)
    do('connect test',              within=3,
                                    expect=connectedToTest, mapper=faberMap)

    do('send NYM dest={target} role=SPONSOR',
                                    within=3,
                                    expect=nymAddedOut, mapper=faberMap)
    return philCli


@pytest.fixture(scope="module")
def acmeAddedByPhil(be, do, poolNodesStarted, philCli, connectedToTest,
                     nymAddedOut, acmeMap):
    be(philCli)
    do('connect test',              within=3,
                                    expect=connectedToTest, mapper=acmeMap)

    do('send NYM dest={target} role=SPONSOR',
                                    within=2,
                                    expect=nymAddedOut, mapper=acmeMap)
    return philCli


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
    be(aliceCli)
    do('show {invite-not-exists}',  expect=fileNotExists, mapper=faberMap)


def testLoadLinkInviteWithoutSig():
    li = getSampleLinkInvitation()
    del li["sig"]
    with pytest.raises(InvalidLinkException) as excinfo:
        Link.validate(li)
    assert "Field not found in given input: sig" in str(excinfo.value)


# def testLoadLinkInviteWithInvalidSig():
#     li = getSampleLinkInvitation()
#     li["sig"] = "invalidsignature"
#     with pytest.raises(InvalidLinkException) as excinfo:
#         Link.validate(li)
#     assert "Signature Rejected" in str(excinfo.value)
#

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
    be(aliceCli)
    do('load {invite}',             expect=loadInviteOut, mapper=faberMap)
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
    if not aliceCli._isConnectedToAnyEnv():
        do('connect test',          within=3,
                                    expect=connectedToTest,
                                    mapper=faberMap)

    do('accept invitation from {inviter}',
                                    within=3,
                                    expect=acceptUnSyncedWithoutEndpointWhenConnected,
                                    mapper=faberMap)


@pytest.fixture(scope="module")
def faberInviteSyncedWithoutEndpoint(be, do, aliceCli, faberMap,
                                     faberInviteLoadedByAlice, poolNodesStarted,
                                     connectedToTest,
                                     faberAddedByPhil,
                                     faberIsRunning,
                                     linkNotYetSynced,
                                     syncLinkOutWithoutEndpoint):
    be(aliceCli)
    if not aliceCli._isConnectedToAnyEnv():
        do('connect test',          within=3,
                                    expect=connectedToTest,
                                    mapper=faberMap)

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


def testEndpointAddedForFaber(faberWithEndpointAdded):
    pass


@pytest.fixture(scope="module")
def faberInviteSyncedWithEndpoint(be, do, faberMap, aliceCLI,
                                  faberInviteSyncedWithoutEndpoint,
                                  faberWithEndpointAdded,
                                  syncLinkOutWithEndpoint,
                                  poolNodesStarted):
    be(aliceCLI)

    do('sync {inviter}',            within=2,
                                    expect=syncLinkOutWithEndpoint,
                                    mapper=faberMap)
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


def testAcceptInviteRespWithInvalidSig(aliceCli, faberAddedByPhil,
                                       faberIsRunning,
                                       faberInviteSyncedWithEndpoint,
                                       faberCli):
    faber, _ = faberIsRunning
    msg = WalletedAgent.createAvailClaimListMsg(faber.getAvailableClaimList())
    sig = aliceCli.activeWallet.signMsg(msg)
    msg[IDENTIFIER] = faberCli.activeWallet.defaultId
    msg[f.SIG.nm] = sig
    aliceCli.agent._handleAcceptInviteResponse((msg, (None, None)))
    assert "Signature rejected" in aliceCli.lastCmdOutput


def acceptInvitation(be, do, userCli, agentMap, expect,
                     totalLinks=None,
                     totalAvailableClaims=None,
                     totalCredDefs=None,
                     totalClaimAttrs=None):
    be(userCli)
    do("accept invitation from {inviter}",
                                    within=10,
                                    mapper=agentMap,
                                    expect=expect,
                                    not_expect=[
                                        "Observer threw an exception",
                                        "Identifier is not yet written to Sovrin"]
                                    )

    if totalLinks:
        assert totalLinks == len(userCli.activeWallet._links)

    if totalAvailableClaims:
        tac = 0
        for li in userCli.activeWallet._links.values():
            tac += len(li.availableClaims)
        assert totalAvailableClaims == tac

    if totalCredDefs:
        assert totalCredDefs == len(userCli.activeWallet._claimDefs)

    if totalClaimAttrs:
        assert totalClaimAttrs == len(userCli.activeWallet._claimAttrs)


@pytest.fixture(scope="module")
def aliceAcceptedFaberInvitation(be, do, aliceCli, faberMap, faberCli,
                                 faberAddedByPhil,
                                 syncedInviteAcceptedWithClaimsOut,
                                 faberLinkAdded, faberIsRunning,
                                 faberInviteSyncedWithEndpoint):
    acceptInvitation(be, do, aliceCli, faberMap,
                     syncedInviteAcceptedWithClaimsOut,
                     totalLinks=1,
                     totalAvailableClaims=1,
                     totalCredDefs=1,
                     totalClaimAttrs=0)
    return aliceCli


def testAliceAcceptFaberInvitation(aliceAcceptedFaberInvitation):
    pass


def testAliceAcceptFaberInvitationAgain(be, do, aliceCli, faberCli, faberMap,
                                        unsycedAlreadyAcceptedInviteAcceptedOut,
                                        aliceAcceptedFaberInvitation):

    li = aliceCli.activeWallet.getLinkInvitationByTarget(
        faberCli.activeWallet.defaultId)
    li.linkStatus = None
    be(aliceCli)

    acceptInvitation(be, do, aliceCli, faberMap,
                     unsycedAlreadyAcceptedInviteAcceptedOut,
                     totalLinks=1,
                     totalAvailableClaims=1,
                     totalCredDefs=1,
                     totalClaimAttrs=0)


def testShowFaberLinkAfterInviteAccept(be, do, aliceCli, faberMap,
                                       showAcceptedLinkOut,
                                       aliceAcceptedFaberInvitation):
    be(aliceCli)

    do("show link {inviter}",       expect=showAcceptedLinkOut,
                                    not_expect="Link (not yet accepted)",
                                    mapper=faberMap)


def testShowClaimNotExists(be, do, aliceCli, faberMap, showClaimNotFoundOut,
                                   aliceAcceptedFaberInvitation):
    be(aliceCli)

    do("show claim claim-to-show-not-exists",
                                    expect=showClaimNotFoundOut,
                                    mapper=faberMap)


def testShowTranscriptClaim(be, do, aliceCli, transcriptClaimMap, showClaimOut,
                                   aliceAcceptedFaberInvitation):

    be(aliceCli)

    do("show claim {name}",
                                    expect=showClaimOut,
                                    mapper=transcriptClaimMap)


def testReqClaimNotExists(be, do, aliceCli, faberMap, showClaimNotFoundOut,
                                   aliceAcceptedFaberInvitation):
    be(aliceCli)

    do("request claim claim-to-req-not-exists",
                                    expect=showClaimNotFoundOut,
                                    mapper=faberMap)


def testReqTranscriptClaim(be, do, aliceCli, transcriptClaimMap, reqClaimOut,
                           faberIsRunning,
                           aliceAcceptedFaberInvitation
                           ):
    be(aliceCli)

    do("request claim {name}",      within=5,
                                    expect=reqClaimOut,
                                    mapper=transcriptClaimMap)


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


def testReqClaimResponseWithInvalidSig(aliceCli, faberCli, faberIsRunning,
                                       faberInviteSyncedWithEndpoint):
    faber, _ = faberIsRunning
    aliceSigner = aliceCli.activeWallet._getIdData(
        aliceCli.activeWallet.defaultId).signer

    msg = WalletedAgent.createClaimMsg(faber.getClaimList())
    msg[IDENTIFIER] = faberCli.activeWallet.defaultId

    reqClaimResp = getSignedRespMsg(msg, aliceSigner)
    aliceCli.agent._handleReqClaimResponse((reqClaimResp, (None, None)))
    assert "Signature rejected" in aliceCli.lastCmdOutput


@pytest.fixture(scope="module")
def aliceRequestedFaberTranscriptClaim(be, do, aliceCli, faberCli,
                                       faberAddedByPhil,
                                       faberLinkAdded,
                                    aliceAcceptedFaberInvitation
                                       ):
    be(aliceCli)
    do("request claim Transcript",  within=5,
                                    expect=[ "Signature accepted.",
                                             "Received Transcript."])
    return aliceCli


def testAliceReqClaim(aliceRequestedFaberTranscriptClaim):
    pass


def testShowFaberClaimPostReqClaim(be, do, aliceCli,
                                   aliceRequestedFaberTranscriptClaim,
                                   transcriptClaimValueMap, rcvdClaimOut):
    be(aliceCli)
    do("show claim {name}",
                                    expect=rcvdClaimOut,
                                    mapper=transcriptClaimValueMap)


def testShowAcmeInvite(be, do, aliceCli, acmeMap):
    be(aliceCli)
    inviteContents = getFileLines(acmeMap.get("invite"))

    do('show {invite}',             expect=inviteContents,
                                    mapper=acmeMap)


@pytest.fixture(scope="module")
def acmeInviteLoadedByAlice(be, do, aliceCli, loadInviteOut, acmeMap):
    be(aliceCli)
    do('load {invite}',             expect=loadInviteOut, mapper=acmeMap)
    link = aliceCli.activeWallet.getLinkInvitation(acmeMap.get("inviter"))
    link.remoteEndPoint = acmeMap.get(ENDPOINT)
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
def acmeAddedByPhil(be, do, poolNodesStarted, philCli, connectedToTest,
                     nymAddedOut, acmeMap):
    be(philCli)
    if not philCli._isConnectedToAnyEnv():
        do('connect test',          within=3,
                                    expect=connectedToTest, mapper=acmeMap)

    do('send NYM dest={target} role=SPONSOR',
                                    within=3,
                                    expect=nymAddedOut, mapper=acmeMap)
    return philCli


@pytest.fixture(scope="module")
def aliceAcceptedAcmeJobInvitation(aliceCli, be, do,
                                   unsycedAcceptedInviteWithoutClaimOut,
                                   aliceRequestedFaberTranscriptClaim,
                                   acmeInviteLoadedByAlice, acmeAddedByPhil,
                                   acmeIsRunning, acmeMap, acmeLinkAdded,
                                   acmeCli, acmeWithEndpointAdded):
    be(aliceCli)
    acceptInvitation(be, do, aliceCli, acmeMap,
                     unsycedAcceptedInviteWithoutClaimOut,
                     totalLinks=2,
                     totalAvailableClaims=1,
                     totalCredDefs=1,
                     totalClaimAttrs=0)
    return aliceCli


def testAliceAcceptAcmeJobInvitation(aliceAcceptedAcmeJobInvitation):
    pass


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


def testSetAttrWithoutContext(be, do, faberCli):
    be(faberCli)
    do("set first_name to Alice",   expect=[
                                            "No context, "
                                            "use below command to "
                                            "set the context"])


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


def testShowJobApplicationClaimReqAfterSetAttr(do,
                                               showJobAppClaimReqOut,
                                               aliceSelfAttestsAttributes):
    do("show claim request {claim-req-to-show}",
                                    expect=showJobAppClaimReqOut,
                                    mapper=aliceSelfAttestsAttributes)


def testInvalidSigErrorResponse(be, do, aliceCli, faberCli, faberMap,
                                faberIsRunning, faberInviteSyncedWithoutEndpoint):

    msg = {
        TYPE: ACCEPT_INVITE,
        IDENTIFIER: faberCli.activeWallet.defaultId,
        NONCE: "unknown"

    }
    signature = aliceCli.activeWallet.signMsg(msg,
                                              aliceCli.activeWallet.defaultId)
    msg[f.SIG.nm] = signature
    ip, port = faberMap[ENDPOINT].split(":")
    aliceCli.sendToAgent(msg, (ip, int(port)))

    be(aliceCli)
    do(None,                        within=3,
                                    expect=["Error (Signature Rejected) "
                                                "occurred while "
                                                "processing this msg: ".
                                                format(msg)])


def testLinkNotFoundErrorResponse(be, do, aliceCli, faberCli, faberMap,
                      faberInviteSyncedWithoutEndpoint):

    msg = {
        TYPE: ACCEPT_INVITE,
        IDENTIFIER: aliceCli.activeWallet.defaultId,
        NONCE: "unknown"
    }
    signature = aliceCli.activeWallet.signMsg(msg,
                                              aliceCli.activeWallet.defaultId)
    msg[f.SIG.nm] = signature
    ip, port = faberMap[ENDPOINT].split(":")
    aliceCli.sendToAgent(msg, (ip, int(port)))

    be(aliceCli)
    do(None,                        within=3,
                                    expect=["Error (No Such Link found) "
                                            "occurred while "
                                            "processing this msg: {}".
                                                format(msg)])


def testAliceSendClaimProofToAcme(be, do, aliceCli, acmeMap,
                                    aliceAcceptedAcmeJobInvitation,
                                  aliceRequestedFaberTranscriptClaim,
                                  aliceSelfAttestsAttributes):
    be(aliceCli)

    do("send claim {claim-req-to-match} to {inviter}",  within=7,
                                expect=["Your claim {claim-req-to-match} "
                                        "{claim-ver-req-to-show} has been received"
                                        " and verified"],
                                mapper=acmeMap)
