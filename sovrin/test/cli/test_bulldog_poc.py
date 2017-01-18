import pytest
from sovrin.common.txn import ENDPOINT
from sovrin.test.cli.helper import getFileLines
from sovrin.test.agent.conftest import runBulldogAgent
from plenum.common.eventually import eventually
from os.path import expanduser, exists
from sovrin.common.config_util import getConfig


def prompt_is(prompt):
    def x(cli):
        assert cli.currPromptText == prompt
    return x


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
def philCli(be, do, philCLI):
    be(philCLI)
    do('prompt Phil', expect=prompt_is('Phil'))

    do('new keyring Phil', expect=['New keyring Phil created',
                                   'Active keyring set to "Phil"'])

    mapper = {
        'seed': '11111111111111111111111111111111',
        'idr': '5rArie7XKukPCaEwq5XGQJnM9Fc5aZE3M9HAPVfMU2xC'}
    do('new key with seed {seed}', expect=['Key created in keyring Phil',
                                           'Identifier for key is {idr}',
                                           'Current identifier set to {idr}'],
       mapper=mapper)

    return philCLI


@pytest.fixture(scope="module")
def bulldogAddedByPhil(be, do, poolNodesStarted, philCli, connectedToTest,
                       nymAddedOut, bulldogMap):
    be(philCli)
    if not philCli._isConnectedToAnyEnv():
        do('connect test', within=3,
           expect=connectedToTest)

    do('send NYM dest={target} role=SPONSOR',
       within=5,
       expect=nymAddedOut, mapper=bulldogMap)
    return philCli


def setPromptAndKeyring(do, name, newKeyringOut, userMap):
    do('prompt {}'.format(name), expect=prompt_is(name))
    do('new keyring {}'.format(name), expect=newKeyringOut, mapper=userMap)


@pytest.fixture(scope="module")
def preRequisite(poolNodesStarted, bulldogAddedByPhil, bulldogIsRunning):
    pass


@pytest.fixture(scope="module")
def earlCli(be, do, earlCLI, newKeyringOut, earlMap):
    be(earlCLI)
    setPromptAndKeyring(do, "Earl", newKeyringOut, earlMap)
    return earlCLI


def testEarlNotConnected(be, do, earlCli, notConnectedStatus):
    be(earlCli)
    do('status', expect=notConnectedStatus)


def connectIfNotAlreadyConnected(do, expectMsgs, userCli, userMap):
    # TODO: Shouldn't this be testing the cli command `status`?
    if not userCli._isConnectedToAnyEnv():
        do('connect test', within=3,
           expect=expectMsgs,
           mapper=userMap)


# Claim Issuance Scenario: Earl obtains proof of banking relationship
def testShowBulldogInvitation(be, do, earlCli, bulldogMap):
    be(earlCli)
    invitationContents = getFileLines(bulldogMap.get("invite"))
    do('show {invite}', expect=invitationContents, mapper=bulldogMap)


def checkWalletStates(userCli,
                      totalLinks,
                      totalAvailableClaims,
                      totalClaimDefs,
                      totalClaimsRcvd,
                      within=None):
    async def check():
        assert totalLinks == len(userCli.activeWallet._links)

        tac = 0
        for li in userCli.activeWallet._links.values():
            tac += len(li.availableClaims)
        assert totalAvailableClaims == tac

        assert totalClaimDefs == len(await userCli.agent.prover.wallet.getAllClaimDef())

        assert totalClaimsRcvd == len((await userCli.agent.prover.wallet.getAllClaims()).keys())

    if within:
        userCli.looper.run(eventually(check, timeout=within))
    else:
        check()


@pytest.fixture(scope="module")
def bulldogInviteLoadedByEarl(be, do, earlCli, loadInviteOut, bulldogMap):
    checkWalletStates(earlCli, totalLinks=0, totalAvailableClaims=0,
                      totalClaimDefs=0, totalClaimsRcvd=0)
    be(earlCli)
    do('load {invite}', expect=loadInviteOut, mapper=bulldogMap)
    checkWalletStates(earlCli, totalLinks=1, totalAvailableClaims=0,
                      totalClaimDefs=0, totalClaimsRcvd=0)
    return earlCli


def testLoadBulldogInvitation(bulldogInviteLoadedByEarl):
    pass


def testShowBulldogLink(be, do, earlCli, bulldogInviteLoadedByEarl,
                        showUnSyncedLinkOut, bulldogMap):
    be(earlCli)
    do('show link {inviter}', expect=showUnSyncedLinkOut,
       mapper=bulldogMap)


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


def syncInvite(be, do, userCli, expectedMsgs, mapping):
    be(userCli)

    do('sync {inviter}', within=2,
       expect=expectedMsgs,
       mapper=mapping)


@pytest.fixture(scope="module")
def bulldogInviteLoadedBySusan(be, do, susanCLI, loadInviteOut, bulldogMap):
    checkWalletStates(earlCli, totalLinks=0, totalAvailableClaims=0,
                      totalClaimDefs=0, totalClaimsRcvd=0)
    be(susanCLI)
    do('load {invite}', expect=loadInviteOut, mapper=bulldogMap)
    checkWalletStates(earlCli, totalLinks=1, totalAvailableClaims=0,
                      totalClaimDefs=0, totalClaimsRcvd=0)
    return susanCLI


def testAcceptUnSyncedBulldogInviteWhenNotConnected(
        be, do, susanCLI,
        poolNodesStarted,
        bulldogAddedByPhil,
        bulldogIsRunning,
        bulldogInviteLoadedBySusan,
        unsyncedInviteAcceptedWhenNotConnected,
        bulldogMap):
    be(susanCLI)
    li = susanCLI.activeWallet.getLinkInvitationByTarget(bulldogMap['target'])
    oldRemoteEndPoint = li.remoteEndPoint
    li.remoteEndPoint = bulldogMap[ENDPOINT]
    do('accept invitation from {inviter}',
       within=5,
       expect=unsyncedInviteAcceptedWhenNotConnected,
       mapper=bulldogMap)
    li.remoteEndPoint = oldRemoteEndPoint


@pytest.fixture(scope="module")
def bulldogInviteSyncedWithoutEndpoint(be, do, earlCli, bulldogMap,
                                       bulldogInviteLoadedByEarl, poolNodesStarted,
                                       connectedToTest,
                                       bulldogAddedByPhil,
                                       bulldogIsRunning,
                                       linkNotYetSynced,
                                       syncLinkOutWithoutEndpoint):
    be(earlCli)
    connectIfNotAlreadyConnected(do, connectedToTest, earlCli, bulldogMap)

    do('sync {inviter}', within=2,
       expect=syncLinkOutWithoutEndpoint,
       mapper=bulldogMap)
    return earlCli


@pytest.fixture(scope="module")
def bulldogWithEndpointAdded(be, do, philCli, bulldogAddedByPhil,
                             bulldogMap, attrAddedOut):
    be(philCli)
    do('send ATTRIB dest={target} raw={endpointAttr}',
       within=3,
       expect=attrAddedOut,
       mapper=bulldogMap)
    return philCli


@pytest.fixture(scope="module")
def bulldogInviteSyncedWithEndpoint(be, do, bulldogMap, earlCLI,
                                    bulldogInviteSyncedWithoutEndpoint,
                                    bulldogWithEndpointAdded,
                                    syncLinkOutWithEndpoint,
                                    poolNodesStarted):
    syncInvite(be, do, earlCLI, syncLinkOutWithEndpoint, bulldogMap)
    return earlCLI


@pytest.fixture(scope="module")
def earlAcceptedBulldogInvitation(be, do, earlCli, bulldogMap,
                                  bulldogAddedByPhil,
                                  syncedInviteAcceptedWithClaimsOut,
                                  bulldogLinkAdded, bulldogIsRunning,
                                  bulldogInviteSyncedWithEndpoint):
    checkWalletStates(earlCli, totalLinks=1, totalAvailableClaims=0,
                      totalClaimDefs=0, totalClaimsRcvd=0)
    acceptInvitation(be, do, earlCli, bulldogMap,
                     syncedInviteAcceptedWithClaimsOut)
    checkWalletStates(earlCli, totalLinks=1, totalAvailableClaims=1,
                      totalClaimDefs=1, totalClaimsRcvd=0)
    return earlCli


def testEarlAcceptBulldogInvitation(earlAcceptedBulldogInvitation):
    pass


@pytest.mark.skipif(True, reason="Incorrect implementation")
def testLogsFilePresentForBulldogAgent(earlAcceptedBulldogInvitation):
    config = getConfig()
    path = expanduser('{}'.format(config.baseDir))
    filePath = '{}/bulldog.log'.format(path)
    assert exists(filePath)


def testShowBankingRelationshipClaim(be, do, earlCli, bankingRelationshipClaimMap,
                                     showBankingRelationshipClaimOut,
                                     earlAcceptedBulldogInvitation):

    be(earlCli)

    do("show claim {name}",
       expect=showBankingRelationshipClaimOut,
       mapper=bankingRelationshipClaimMap,
       within=5)


@pytest.fixture(scope="module")
def earlRequestedBankingRelationshipClaim(be, do, earlCli, bankingRelationshipClaimMap,
                                          reqClaimOut,
                                          bulldogIsRunning,
                                          earlAcceptedBulldogInvitation):
    be(earlCli)
    checkWalletStates(earlCli, totalLinks=1, totalAvailableClaims=1,
                      totalClaimDefs=1, totalClaimsRcvd=0)
    do("request claim {name}", within=5,
       expect=reqClaimOut,
       mapper=bankingRelationshipClaimMap)

    checkWalletStates(earlCli, totalLinks=1, totalAvailableClaims=1,
                      totalClaimDefs=1, totalClaimsRcvd=1, within=2)


def testEarlRequestedBankingRelationshipClaim(earlRequestedBankingRelationshipClaim):
    pass


def testShowBankingRelationshipClaimPostReqClaim(be, do, earlCli,
                                                 earlRequestedBankingRelationshipClaim,
                                                 bankingRelationshipClaimValueMap,
                                                 rcvdBankingRelationshipClaimOut):
    be(earlCli)
    do("show claim {name}",
       expect=rcvdBankingRelationshipClaimOut,
       mapper=bankingRelationshipClaimValueMap,
       within=3)


# Proof Presentation Scenario: Earl applies for home insurance
@pytest.fixture(scope="module")
def bulldogInsuranceInvitationLoadedByEarl(be, do, earlCli,
                                       nextCommandsToTryUsageLine,
                                       bulldogMap,
                                       earlRequestedBankingRelationshipClaim):
    be(earlCli)
    do('load {invite-insurance}', expect=nextCommandsToTryUsageLine, mapper=bulldogMap)


def testLoadBulldogInsuranceInvitation(bulldogInsuranceInvitationLoadedByEarl):
    pass


def testShowBulldogInsuranceLink(be, do, earlCli,
                                 bulldogInsuranceInvitationLoadedByEarl,
                                 showAcceptedSyncedLinkOut,
                                 bulldogMap):
    be(earlCli)
    do('show link {inviter}',
       expect=showAcceptedSyncedLinkOut,
       mapper=bulldogMap,
       within=5)


def testShowBulldogInsuranceClaimReq(be, do, earlCli, bulldogMap,
                                     bulldogInsuranceClaimReqMap,
                                     bankingRelationshipClaimAttrValueMap,
                                     bulldogInsuranceInvitationLoadedByEarl,
                                     showBulldogInsuranceClaimReqOut):
    be(earlCli)
    mapping = {}
    mapping.update(bulldogMap)
    mapping.update(bulldogInsuranceClaimReqMap)
    mapping.update(bankingRelationshipClaimAttrValueMap)

    do("show claim request {claim-req-to-show}",
       expect=showBulldogInsuranceClaimReqOut,
       mapper=mapping,
       within=3)


def sendClaim(be, do, userCli, agentMap, extraMsgs=None):
    be(userCli)

    expectMsgs = [
        "Your claim {claim-req-to-match} "
        "{claim-ver-req-to-show} was "
        "received and verified"
    ]
    if extraMsgs:
        expectMsgs.extend(extraMsgs)
    mapping = {}
    mapping.update(agentMap)

    do("send claim {claim-req-to-match} to {inviter}",
       within=7,
       expect=expectMsgs,
       mapper=mapping)


@pytest.fixture(scope="module")
def insuranceApplicationClaimSent(be, do, earlCli,
                                  bulldogMap,
                                  bulldogInsuranceInvitationLoadedByEarl):
    return lambda: sendClaim(be, do, earlCli, bulldogMap)


def testEarlSendClaimProofToBulldog(insuranceApplicationClaimSent):
    insuranceApplicationClaimSent()


# def testEarlSendClaimProofAfterAgentRestart(insuranceApplicationClaimSent,
#                                             bulldogAgent, emptyLooper,
#                                             bulldogWallet):
#     insuranceApplicationClaimSent()
#     # stop agent
#     bulldogAgent.stop()
#     emptyLooper.removeProdable()
#     # start agent again
#     runBulldogAgent(emptyLooper, bulldogWallet, bulldogAgent)
#     # send claim again
#     insuranceApplicationClaimSent()
#     # it should fail for now
