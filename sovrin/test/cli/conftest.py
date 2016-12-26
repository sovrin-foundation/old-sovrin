import json
import traceback

import plenum
import pytest
from plenum.common.raet import initLocalKeep
from plenum.test.eventually import eventually

from sovrin.cli.helper import USAGE_TEXT, NEXT_COMMANDS_TO_TRY_TEXT
from sovrin.common.txn import SPONSOR, ENDPOINT
from sovrin.test.helper import createNym, buildStewardClient

plenum.common.util.loggingConfigured = False

from plenum.common.looper import Looper
from plenum.test.cli.helper import newKeyPair, checkAllNodesStarted, \
    checkCmdValid

from sovrin.common.config_util import getConfig
from sovrin.test.cli.helper import newCLI, ensureNodesCreated, getLinkInvitation
from sovrin.test.agent.conftest import faberIsRunning as runningFaber, \
    emptyLooper, faberWallet, faberLinkAdded, acmeWallet, acmeLinkAdded, \
    acmeIsRunning as runningAcme, faberAgentPort, acmeAgentPort, faberAgent, \
    acmeAgent, thriftIsRunning as runningThrift, thriftAgentPort, thriftWallet,\
    thriftAgent

config = getConfig()


@pytest.yield_fixture(scope="module")
def looper():
    with Looper(debug=False) as l:
        yield l


# TODO: Probably need to remove
@pytest.fixture("module")
def nodesCli(looper, tdir, nodeNames):
    cli = newCLI(looper, tdir)
    cli.enterCmd("new node all")
    checkAllNodesStarted(cli, *nodeNames)
    return cli


@pytest.fixture("module")
def cli(looper, tdir):
    return newCLI(looper, tdir)


@pytest.fixture(scope="module")
def newKeyPairCreated(cli):
    return newKeyPair(cli)


@pytest.fixture(scope="module")
def CliBuilder(tdir, tdirWithPoolTxns, tdirWithDomainTxns, tconf):
    def _(subdir, looper=None):
        def new():
            return newCLI(looper,
                          tdir,
                          subDirectory=subdir,
                          conf=tconf,
                          poolDir=tdirWithPoolTxns,
                          domainDir=tdirWithDomainTxns)
        if looper:
            yield new()
        else:
            with Looper(debug=False) as looper:
                yield new()
    return _


@pytest.fixture(scope="module")
def aliceMap():
    return {
        'keyring-name': 'Alice',
    }


@pytest.fixture(scope="module")
def susanMap():
    return {
        'keyring-name': 'Susan',
    }


@pytest.fixture(scope="module")
def faberMap(faberAgentPort):
    endpoint = "127.0.0.1:{}".format(faberAgentPort)
    return {'inviter': 'Faber College',
            'invite': "sample/faber-invitation.sovrin",
            'invite-not-exists': "sample/faber-invitation.sovrin.not.exists",
            'inviter-not-exists': "non-existing-inviter",
            "target": "FuN98eH2eZybECWkofW6A9BKJxxnTatBCopfUiNxo6ZB",
            "nonce": "b1134a647eb818069c089e7694f63e6d",
            ENDPOINT: endpoint,
            "endpointAttr": json.dumps({ENDPOINT: endpoint}),
            "claims": "Transcript",
            "claim-to-show": "Transcript",
            "claim-req-to-match": "Transcript",
            }


@pytest.fixture(scope="module")
def acmeMap(acmeAgentPort):
    endpoint = "127.0.0.1:{}".format(acmeAgentPort)
    return {'inviter': 'Acme Corp',
            'invite': "sample/acme-job-application.sovrin",
            'invite-not-exists': "sample/acme-job-application.sovrin.not.exists",
            'inviter-not-exists': "non-existing-inviter",
            "target": "7YD5NKn3P4wVJLesAmA1rr7sLPqW9mR1nhFdKD518k21",
            "nonce": "57fbf9dc8c8e6acde33de98c6d747b28c",
            ENDPOINT: endpoint,
            "endpointAttr": json.dumps({ENDPOINT: endpoint}),
            "claim-requests" : "Job-Application",
            "claim-req-to-show": "Job-Application",
            "claim-ver-req-to-show": "0.2",
            "claim-req-to-match": "Job-Application",
            "claims": "<claim-name>",
            "rcvd-claim-transcript-provider": "Faber College",
            "rcvd-claim-transcript-name": "Transcript",
            "rcvd-claim-transcript-version": "1.2"
            }


@pytest.fixture(scope="module")
def thriftMap(thriftAgentPort):
    endpoint = "127.0.0.1:{}".format(thriftAgentPort)
    return {'inviter': 'Thrift Bank',
            'invite': "sample/thrift-loan-application.sovrin",
            'invite-not-exists': "sample/thrift-loan-application.sovrin.not.exists",
            'inviter-not-exists': "non-existing-inviter",
            "target": "9jegUr9vAMqoqQQUEAiCBYNQDnUbTktQY9nNspxfasZW",
            "nonce": "77fbf9dc8c8e6acde33de98c6d747b28c",
            ENDPOINT: endpoint,
            "endpointAttr": json.dumps({ENDPOINT: endpoint}),
            "claim-requests": "Loan-Application-Basic, Loan-Application-KYC",
            "claim-ver-req-to-show": "0.1"
            }


@pytest.fixture(scope="module")
def loadInviteOut(nextCommandsToTryUsageLine):
    return ["1 link invitation found for {inviter}.",
            "Creating Link for {inviter}.",
            "Generating Identifier and Signing key."] + \
           nextCommandsToTryUsageLine + \
           ['accept invitation from "{inviter}"',
            'show link "{inviter}"']


@pytest.fixture(scope="module")
def fileNotExists():
    return ["Given file does not exist"]


@pytest.fixture(scope="module")
def connectedToTest():
    return ["Connected to test"]


@pytest.fixture(scope="module")
def canNotSyncMsg():
    return ["Cannot sync because not connected"]


@pytest.fixture(scope="module")
def syncWhenNotConnected(canNotSyncMsg, connectUsage):
    return canNotSyncMsg + connectUsage


@pytest.fixture(scope="module")
def canNotAcceptMsg():
    return ["Cannot accept because not connected"]


@pytest.fixture(scope="module")
def acceptWhenNotConnected(canNotAcceptMsg, connectUsage):
    return canNotAcceptMsg + connectUsage


@pytest.fixture(scope="module")
def acceptUnSyncedWithoutEndpointWhenConnected(commonAcceptInvitationMsgs):
    return commonAcceptInvitationMsgs


@pytest.fixture(scope="module")
def commonAcceptInvitationMsgs():
    return ["Invitation not yet verified",
            "Link not yet synchronized.",
            ]


@pytest.fixture(scope="module")
def acceptUnSyncedWhenNotConnected(commonAcceptInvitationMsgs,
                                   canNotSyncMsg, connectUsage):
    return commonAcceptInvitationMsgs + \
            ["Invitation acceptance aborted."] + \
            canNotSyncMsg + connectUsage


@pytest.fixture(scope="module")
def usageLine():
    return [USAGE_TEXT]


@pytest.fixture(scope="module")
def nextCommandsToTryUsageLine():
    return [NEXT_COMMANDS_TO_TRY_TEXT]


@pytest.fixture(scope="module")
def connectUsage(usageLine):
    return usageLine + ["connect <test|live>"]


@pytest.fixture(scope="module")
def notConnectedStatus(connectUsage):
    return ['Not connected to Sovrin network. Please connect first.'] +\
            connectUsage


@pytest.fixture(scope="module")
def newKeyringOut():
    return ["New keyring {keyring-name} created",
            'Active keyring set to "{keyring-name}"'
            ]


@pytest.fixture(scope="module")
def linkAlreadyExists():
    return ["Link already exists"]


@pytest.fixture(scope="module")
def jobApplicationClaimReqMap():
    return {
        'claim-req-version': '0.2',
        'claim-req-attr-first_name': 'first_name',
        'claim-req-attr-last_name': 'last_name',
        'claim-req-attr-phone_number': 'phone_number',
        'claim-req-attr-degree': 'degree',
        'claim-req-attr-status': 'status',
        'claim-req-attr-ssn': 'ssn'
    }


@pytest.fixture(scope="module")
def syncedInviteAcceptedOutWithoutClaims():
    return [
        "Signature accepted.",
        "Trust established.",
        "Identifier created in Sovrin.",
        "Synchronizing...",
        "Confirmed identifier written to Sovrin."
    ]


@pytest.fixture(scope="module")
def syncedInviteAcceptedWithClaimsOut(syncedInviteAcceptedOutWithoutClaims):
    return syncedInviteAcceptedOutWithoutClaims + [
        "Available Claim(s): {claims}",
    ]


@pytest.fixture(scope="module")
def unsycedAcceptedInviteWithoutClaimOut(syncedInviteAcceptedOutWithoutClaims):
    return [
        "Invitation not yet verified",
        "Attempting to sync...",
        "Synchronizing...",
    ] + syncedInviteAcceptedOutWithoutClaims + \
           ["Confirmed identifier written to Sovrin."]


@pytest.fixture(scope="module")
def unsycedAlreadyAcceptedInviteAcceptedOut():
    return [
        "Invitation not yet verified",
        "Attempting to sync...",
        "Synchronizing...",
        "Already accepted"
    ]


@pytest.fixture(scope="module")
def showTranscriptClaimProofOut():
    return [
        "Claim proof ({rcvd-claim-transcript-name} "
        "v{rcvd-claim-transcript-version} "
        "from {rcvd-claim-transcript-provider})",
        "student_name: {attr-student_name}",
        "ssn: {attr-ssn}",
        "degree: {attr-degree}",
        "year: {attr-year}",
        "status: {attr-status}",
    ]


@pytest.fixture(scope="module")
def showJobAppClaimReqOut(showTranscriptClaimProofOut):
    return [
        'Found claim request "{claim-req-to-match}" in link "{inviter}"',
        "Name: {claim-req-to-show}",
        "Version: {claim-req-version}",
        "Status: Requested",
        "Attributes:",
        "{claim-req-attr-first_name}: {set-attr-first_name}",
        "{claim-req-attr-last_name}: {set-attr-last_name}",
        "{claim-req-attr-phone_number}: {set-attr-phone_number}",
        "{claim-req-attr-degree}: {attr-degree}",
        "{claim-req-attr-status}: {attr-status}",
        "{claim-req-attr-ssn}: {attr-ssn}"
    ] + showTranscriptClaimProofOut


@pytest.fixture(scope="module")
def claimReqNotExists():
    return ["No matching claim request(s) found in current keyring"]


@pytest.fixture(scope="module")
def linkNotExists():
    return ["No matching link invitation(s) found in current keyring"]


@pytest.fixture(scope="module")
def faberInviteLoaded(aliceCLI, be, do, faberMap, loadInviteOut):
    be(aliceCLI)
    do("load {invite}", expect=loadInviteOut, mapper=faberMap)


@pytest.fixture(scope="module")
def acmeInviteLoaded(aliceCLI, be, do, acmeMap, loadInviteOut):
    be(aliceCLI)
    do("load {invite}", expect=loadInviteOut, mapper=acmeMap)


@pytest.fixture(scope="module")
def attrAddedOut():
    return ["Attribute added for nym {target}"]


@pytest.fixture(scope="module")
def nymAddedOut():
    return ["Nym {target} added"]


@pytest.fixture(scope="module")
def unSyncedEndpointOut():
    return ["Target endpoint: <unknown, waiting for sync>"]


@pytest.fixture(scope="module")
def showLinkOutWithoutEndpoint(showLinkOut, unSyncedEndpointOut):
    return showLinkOut + unSyncedEndpointOut


@pytest.fixture(scope="module")
def endpointReceived():
    return ["Endpoint received:"]


@pytest.fixture(scope="module")
def endpointNotAvailable():
    return ["Endpoint not available"]


@pytest.fixture(scope="module")
def syncLinkOutEndsWith():
    return ["Link {inviter} synced"]


@pytest.fixture(scope="module")
def syncLinkOutStartsWith():
    return ["Synchronizing..."]


@pytest.fixture(scope="module")
def syncLinkOutWithEndpoint(syncLinkOutStartsWith,
                            syncLinkOutEndsWith):
    return syncLinkOutStartsWith + syncLinkOutEndsWith


@pytest.fixture(scope="module")
def syncLinkOutWithoutEndpoint(syncLinkOutStartsWith):
    return syncLinkOutStartsWith


@pytest.fixture(scope="module")
def showSyncedLinkWithEndpointOut(acceptedLinkHeading, showLinkOut):
    return acceptedLinkHeading + showLinkOut + \
        ["Last synced: "] + \
        ["Target endpoint: {endpoint}"]


@pytest.fixture(scope="module")
def showSyncedLinkWithoutEndpointOut(showLinkOut):
    return showLinkOut


@pytest.fixture(scope="module")
def linkNotYetSynced():
    return ["Last synced: <this link has not yet been synchronized>"]


@pytest.fixture(scope="module")
def acceptedLinkHeading():
    return ["Link"]


@pytest.fixture(scope="module")
def unAcceptedLinkHeading():
    return ["Link (not yet accepted)"]


@pytest.fixture(scope="module")
def showUnSyncedLinkOut(unAcceptedLinkHeading, showLinkOut, linkNotYetSynced):
    return unAcceptedLinkHeading + showLinkOut + linkNotYetSynced


@pytest.fixture(scope="module")
def showClaimNotFoundOut():
    return [ "No matching claim(s) found in any links in current keyring"
    ]


@pytest.fixture(scope="module")
def transcriptClaimAttrValueMap():
    return {
        "attr-student_name": "Alice Garcia",
        "attr-ssn": "123-45-6789",
        "attr-degree": "Bachelor of Science, Marketing",
        "attr-year": "2015",
        "attr-status": "graduated"
    }


@pytest.fixture(scope="module")
def transcriptClaimValueMap(transcriptClaimAttrValueMap):
    basic = {
        'inviter': 'Faber College',
        'name': 'Transcript',
        "version": "1.2",
        'status': "available (not yet issued)"
    }
    basic.update(transcriptClaimAttrValueMap)
    return basic


@pytest.fixture(scope="module")
def transcriptClaimMap():
    return {
        'inviter': 'Faber College',
        'name': 'Transcript',
        'status': "available (not yet issued)",
        "version": "1.2",
        "attr-student_name": "string",
        "attr-ssn": "string",
        "attr-degree": "string",
        "attr-year": "string",
        "attr-status": "string"
    }


@pytest.fixture(scope="module")
def jobCertClaimAttrValueMap():
    return {
        "attr-first_name": "Alice",
        "attr-last_name": "Garcia",
        "attr-employee_status": "Permanent",
        "attr-experience": "3 years",
        "attr-salary_bracket": "between $50,000 to $100,000"
    }


@pytest.fixture(scope="module")
def jobCertificateClaimValueMap(jobCertClaimAttrValueMap):
    basic = {
        'inviter': 'Acme Corp',
        'name': 'Job-Certificate',
        'status': "available (not yet issued)",
        "version": "0.2"
    }
    basic.update(jobCertClaimAttrValueMap)
    return basic


@pytest.fixture(scope="module")
def jobCertificateClaimMap():
    return {
        'inviter': 'Acme Corp',
        'name': 'Job-Certificate',
        'status': "available (not yet issued)",
        "version": "0.2",
        "attr-first_name": "string",
        "attr-last_name": "string",
        "attr-employee_status": "string",
        "attr-experience": "string",
        "attr-salary_bracket": "string"
    }


@pytest.fixture(scope="module")
def reqClaimOut():
    return ["Found claim {name} in link {inviter}",
            "Requesting claim {name} from {inviter}..."]


# TODO Change name
@pytest.fixture(scope="module")
def reqClaimOut1():
    return ["Found claim {name} in link {inviter}",
            "Requesting claim {name} from {inviter}...",
            "Signature accepted.",
            'Received claim "{name}".']


@pytest.fixture(scope="module")
def rcvdTranscriptClaimOut():
    return ["Found claim {name} in link {inviter}",
            "Name: {name}",
            "Status: ",
            "Version: {version}",
            "Attributes:",
            "student_name: {attr-student_name}",
            "ssn: {attr-ssn}",
            "degree: {attr-degree}",
            "year: {attr-year}",
            "status: {attr-status}"
    ]


@pytest.fixture(scope="module")
def rcvdJobCertClaimOut():
    return ["Found claim {name} in link {inviter}",
            "Name: {name}",
            "Status: ",
            "Version: {version}",
            "Attributes:",
            "first_name: {attr-first_name}",
            "last_name: {attr-last_name}",
            "employee_status: {attr-employee_status}",
            "experience: {attr-experience}",
            "salary_bracket: {attr-salary_bracket}"
    ]


@pytest.fixture(scope="module")
def showTranscriptClaimOut(nextCommandsToTryUsageLine):
    return ["Found claim {name} in link {inviter}",
            "Name: {name}",
            "Status: {status}",
            "Version: {version}",
            "Attributes:",
            "student_name",
            "ssn",
            "degree",
            "year",
            "status"
            ] + nextCommandsToTryUsageLine + \
           ['request claim "{name}"']


@pytest.fixture(scope="module")
def showJobCertClaimOut(nextCommandsToTryUsageLine):
    return ["Found claim {name} in link {inviter}",
            "Name: {name}",
            "Status: {status}",
            "Version: {version}",
            "Attributes:",
            "first_name",
            "last_name",
            "employee_status",
            "experience",
            "salary_bracket"
            ] + nextCommandsToTryUsageLine + \
           ['request claim "{name}"']


@pytest.fixture(scope="module")
def showLinkWithClaimReqOut():
    return ["Claim Request(s): {claim-requests}"]


@pytest.fixture(scope="module")
def showLinkWithAvailableClaimsOut():
    return ["Available Claim(s): {claims}"]


@pytest.fixture(scope="module")
def showAcceptedLinkWithClaimReqsOut(showAcceptedLinkOut,
                                     showLinkWithClaimReqOut,
                                     showLinkWithAvailableClaimsOut,
                                     showLinkSuggestion):
    return showAcceptedLinkOut + showLinkWithClaimReqOut + \
           showLinkWithAvailableClaimsOut + \
           showLinkSuggestion


@pytest.fixture(scope="module")
def showAcceptedLinkWithoutAvailableClaimsOut(showAcceptedLinkOut,
                                        showLinkWithClaimReqOut):
    return showAcceptedLinkOut + showLinkWithClaimReqOut


@pytest.fixture(scope="module")
def showAcceptedLinkWithAvailableClaimsOut(showAcceptedLinkOut,
                                           showLinkWithClaimReqOut,
                                           showLinkWithAvailableClaimsOut):
    return showAcceptedLinkOut + showLinkWithClaimReqOut + \
           showLinkWithAvailableClaimsOut


@pytest.fixture(scope="module")
def showLinkSuggestion(nextCommandsToTryUsageLine):
    return nextCommandsToTryUsageLine + \
    ['show claim "{claims}"',
     'request claim "{claims}"']


@pytest.fixture(scope="module")
def showAcceptedLinkOut():
    return [
            "Link",
            "Name: {inviter}",
            "Target: {target}",
            "Target Verification key: <same as target>",
            "Trust anchor: {inviter} (confirmed)",
            "Invitation nonce: {nonce}",
            "Invitation status: Accepted"]


@pytest.fixture(scope="module")
def showLinkOut(nextCommandsToTryUsageLine):
    return [
            "Name: {inviter}",
            "Target: {target}",
            "Target Verification key: <unknown, waiting for sync>",
            "Trust anchor: {inviter} (not yet written to Sovrin)",
            "Invitation nonce: {nonce}",
            "Invitation status: not verified, target verkey unknown"] + \
           nextCommandsToTryUsageLine + \
           ['accept invitation from "{inviter}"',
            'sync "{inviter}"']


@pytest.yield_fixture(scope="module")
def poolCLI_baby(CliBuilder):
    yield from CliBuilder("pool")


@pytest.yield_fixture(scope="module")
def aliceCLI(CliBuilder):
    yield from CliBuilder("alice")


@pytest.yield_fixture(scope="module")
def susanCLI(CliBuilder):
    yield from CliBuilder("susan")


@pytest.yield_fixture(scope="module")
def philCLI(CliBuilder):
    yield from CliBuilder("phil")


@pytest.fixture(scope="module")
def poolCLI(poolCLI_baby, poolTxnData, poolTxnNodeNames):
    seeds = poolTxnData["seeds"]
    for nName in poolTxnNodeNames:
        initLocalKeep(nName,
                      poolCLI_baby.basedirpath,
                      seeds[nName],
                      override=True)
    return poolCLI_baby


@pytest.fixture(scope="module")
def poolNodesCreated(poolCLI, poolTxnNodeNames):
    ensureNodesCreated(poolCLI, poolTxnNodeNames)
    return poolCLI


@pytest.fixture("module")
def ctx():
    """
    Provides a simple container for test context. Assists with 'be' and 'do'.
    """
    return {}


@pytest.fixture("module")
def be(ctx):
    """
    Fixture that is a 'be' function that closes over the test context.
    'be' allows to change the current cli in the context.
    """
    def _(cli):
        ctx['current_cli'] = cli
    return _


@pytest.fixture("module")
def do(ctx):
    """
    Fixture that is a 'do' function that closes over the test context
    'do' allows to call the do method of the current cli from the context.
    """
    def _(attempt, expect=None, within=None, mapper=None, not_expect=None):
        cli = ctx['current_cli']

        # This if was not there earlier, but I felt a need to reuse this
        # feature (be, do, expect ...) without attempting anything
        # mostly because there will be something async which will do something,
        # hence I added the below if check

        if attempt:
            attempt = attempt.format(**mapper) if mapper else attempt
            checkCmdValid(cli, attempt)

        def check():
            nonlocal expect
            nonlocal not_expect

            def chk(obj, parity=True):
                if not obj:
                    return
                if isinstance(obj, str) or callable(obj):
                    obj = [obj]
                for e in obj:
                    if isinstance(e, str):
                        e = e.format(**mapper) if mapper else e
                        if parity:
                            assert e in cli.lastCmdOutput
                        else:
                            assert e not in cli.lastCmdOutput
                    elif callable(e):
                        # callables should raise exceptions to signal an error
                        if parity:
                            e(cli)
                        else:
                            try:
                                e(cli)
                            except:
                                # Since its a test so not using logger is not
                                # a big deal
                                traceback.print_exc()
                                continue
                            raise RuntimeError("did not expect success")
                    else:
                        raise AttributeError("only str, callable, or "
                                             "collections of str and callable "
                                             "are allowed")
            chk(expect)
            chk(not_expect, False)
        if within:
            cli.looper.run(eventually(check, timeout=within))
        else:
            check()
    return _


@pytest.fixture(scope="module")
def steward(poolNodesCreated, looper, tdir, stewardWallet):
    return buildStewardClient(looper, tdir, stewardWallet)


@pytest.fixture(scope="module")
def faberAdded(poolNodesCreated,
             looper,
             aliceCLI,
             faberInviteLoaded,
             aliceConnected,
            steward, stewardWallet):
    li = getLinkInvitation("Faber", aliceCLI.activeWallet)
    createNym(looper, li.remoteIdentifier, steward, stewardWallet,
              role=SPONSOR)


@pytest.fixture(scope="module")
def faberIsRunning(emptyLooper, tdirWithPoolTxns, faberWallet,
                   faberAddedByPhil, faberAgent):
    faber, faberWallet = runningFaber(emptyLooper, tdirWithPoolTxns,
                                      faberWallet, faberAgent, faberAddedByPhil)
    return faber, faberWallet


@pytest.fixture(scope="module")
def acmeIsRunning(emptyLooper, tdirWithPoolTxns, acmeWallet,
                   acmeAddedByPhil, acmeAgent):
    acme, acmeWallet = runningAcme(emptyLooper, tdirWithPoolTxns,
                                   acmeWallet, acmeAgent, acmeAddedByPhil)

    return acme, acmeWallet


@pytest.fixture(scope="module")
def thriftIsRunning(emptyLooper, tdirWithPoolTxns, thriftWallet,
                    thriftAddedByPhil, thriftAgent):
    thrift, thriftWallet = runningThrift(emptyLooper, tdirWithPoolTxns,
                                         thriftWallet, thriftAgent,
                                         thriftAddedByPhil)

    return thrift, thriftWallet


@pytest.fixture(scope="module")
def claimDefAdded():
    return ["credential definition is published"]


@pytest.fixture(scope="module")
def issuerKeyAdded():
    return ["issuer key is published"]