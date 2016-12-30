import json
import logging
import re

import pytest
from plenum.common.eventually import eventually

from anoncreds.protocol.types import ClaimDefinitionKey, ID
from sovrin.agent.agent import createAndRunAgent
from sovrin.common.setup_util import Setup
from sovrin.common.txn import ENDPOINT
from sovrin.test.agent.acme import AcmeAgent
from sovrin.test.agent.faber import FaberAgent
from sovrin.test.agent.helper import buildFaberWallet, buildAcmeWallet, \
    buildThriftWallet
from sovrin.test.agent.thrift import ThriftAgent
from sovrin.test.cli.conftest import faberMap, acmeMap, \
    thriftMap
from sovrin.test.cli.helper import newCLI
from sovrin.test.cli.test_tutorial import syncInvite, acceptInvitation, \
    aliceRequestedTranscriptClaim, jobApplicationClaimSent, \
    jobCertClaimRequested, bankBasicClaimSent, bankKYCClaimSent, \
    setPromptAndKeyring, poolNodesStarted
from sovrin.test.helper import TestClient

concerningLogLevels = [logging.WARNING,
                       logging.ERROR,
                       logging.CRITICAL]


def getSeqNoFromCliOutput(cli):
    seqPat = re.compile("Sequence number is ([0-9]+)")
    m = seqPat.search(cli.lastCmdOutput)
    assert m
    seqNo, = m.groups()
    return seqNo


@pytest.fixture(scope="module")
def newGuyCLI(looper, tdir, tconf):
    Setup(tdir).setupAll()
    return newCLI(looper, tdir, subDirectory='newguy', conf=tconf)


@pytest.mark.skip("Not yet implemented")
def testGettingStartedTutorialAgainstSandbox(newGuyCLI, be, do):
    be(newGuyCLI)
    do('connect test', within=3, expect="Connected to test")
    # TODO finish the entire set of steps


def testManual(do, be, poolNodesStarted, poolTxnStewardData, philCLI,
               connectedToTest, nymAddedOut, attrAddedOut,
               claimDefAdded, issuerKeyAdded, aliceCLI, newKeyringOut, aliceMap,
               tdir, syncLinkOutWithEndpoint, jobCertificateClaimMap,
               syncedInviteAcceptedOutWithoutClaims, transcriptClaimMap,
               reqClaimOut, reqClaimOut1, susanCLI, susanMap):
    eventually.slowFactor = 3

    # Create steward and add nyms and endpoint atttributes of all agents
    _, stewardSeed = poolTxnStewardData
    be(philCLI)
    do('new keyring Steward', expect=['New keyring Steward created',
                                      'Active keyring set to "Steward"'])

    mapper = {'seed': stewardSeed.decode()}
    do('new key with seed {seed}', expect=['Key created in keyring Steward'],
       mapper=mapper)
    do('connect test', within=3, expect=connectedToTest)

    # Add nym and endpoint for Faber, Acme and Thrift
    agentIpAddress = "127.0.0.1"
    faberAgentPort = 5555
    acmeAgentPort = 6666
    thriftAgentPort = 7777
    faberEndpoint = "{}:{}".format(agentIpAddress, faberAgentPort)
    acmeEndpoint = "{}:{}".format(agentIpAddress, acmeAgentPort)
    thriftEndpoint = "{}:{}".format(agentIpAddress, thriftAgentPort)

    for nym, ep in [('FuN98eH2eZybECWkofW6A9BKJxxnTatBCopfUiNxo6ZB', faberEndpoint),
                    ('7YD5NKn3P4wVJLesAmA1rr7sLPqW9mR1nhFdKD518k21', acmeEndpoint),
                    ('9jegUr9vAMqoqQQUEAiCBYNQDnUbTktQY9nNspxfasZW', thriftEndpoint)]:
        m = {'target': nym, 'endpoint': json.dumps({ENDPOINT: ep})}
        do('send NYM dest={target} role=SPONSOR',
           within=3, expect=nymAddedOut, mapper=m)
        do('send ATTRIB dest={target} raw={endpoint}', within=3,
           expect=attrAddedOut, mapper=m)

    # Start Faber Agent and Acme Agent

    fMap = faberMap(agentIpAddress, faberAgentPort)
    aMap = acmeMap(agentIpAddress, acmeAgentPort)
    tMap = thriftMap(agentIpAddress, thriftAgentPort)

    agentParams = [
        (FaberAgent, "Faber College", faberAgentPort,
         buildFaberWallet),
        (AcmeAgent, "Acme Corp", acmeAgentPort,
         buildAcmeWallet),
        (ThriftAgent, "Thrift Bank", thriftAgentPort,
         buildThriftWallet)
    ]

    for agentCls, agentName, agentPort, buildAgentWalletFunc in \
            agentParams:
        agentCls.getPassedArgs = lambda _: (agentPort,)
        createAndRunAgent(agentCls, agentName, buildAgentWalletFunc(), tdir, agentPort, philCLI.looper, TestClient)

    for p in philCLI.looper.prodables:
        if p.name == 'Faber College':
            faberAgent = p
        if p.name == 'Acme Corp':
            acmeAgent = p
        if p.name == 'Thrift Bank':
            thriftAgent = p

    async def checkTranscriptWritten():
        faberId = faberAgent.wallet.defaultId
        claimDefId = ID(ClaimDefinitionKey("Transcript", "1.2", faberId))
        claimDef = await faberAgent.issuer.wallet.getClaimDef(claimDefId)
        assert claimDef
        assert claimDef.seqId

        issuerKey = faberAgent.issuer.wallet.getPublicKey(claimDefId)
        assert issuerKey

    async def checkJobCertWritten():
        acmeId = acmeAgent.wallet.defaultId
        claimDefId = ID(ClaimDefinitionKey("Job-Certificate", "0.2", acmeId))
        claimDef = await acmeAgent.issuer.wallet.getClaimDef(claimDefId)
        assert claimDef
        assert claimDef.seqId

        issuerKey = await acmeAgent.issuer.wallet.getPublicKey(claimDefId)
        assert issuerKey
        assert issuerKey.seqId

    philCLI.looper.run(eventually(checkTranscriptWritten, timeout=10))
    philCLI.looper.run(eventually(checkJobCertWritten, timeout=10))

    # Defining inner method for closures
    def executeGstFlow(name, userCLI, userMap, be, connectedToTest, do, fMap,
                       aMap, jobCertificateClaimMap, newKeyringOut, reqClaimOut,
                       reqClaimOut1, syncLinkOutWithEndpoint,
                       syncedInviteAcceptedOutWithoutClaims, tMap,
                       transcriptClaimMap):

        async def getPublicKey(wallet, claimDefId):
            return await wallet.getPublicKey(claimDefId)

        async def getClaim(claimDefId):
            return userCLI.agent.prover.wallet.getClaims(claimDefId)

        # Start User cli

        be(userCLI)
        setPromptAndKeyring(do, name, newKeyringOut, userMap)
        do('connect test', within=3, expect=connectedToTest)
        # Accept faber
        do('load sample/faber-invitation.sovrin')
        syncInvite(be, do, userCLI, syncLinkOutWithEndpoint, fMap)
        do('show link faber')
        acceptInvitation(be, do, userCLI, fMap,
                         syncedInviteAcceptedOutWithoutClaims)
        # Request claim
        do('show claim Transcript')
        aliceRequestedTranscriptClaim(be, do, userCLI, transcriptClaimMap,
                                      reqClaimOut,
                                      None,  # Passing None since its not used
                                      None)  # Passing None since its not used

        faberClaimDefId = ID(ClaimDefinitionKey('Transcript', '1.2', fMap['target']))
        faberIssuerKey = userCLI.looper.run(getPublicKey(faberAgent.issuer.wallet, faberClaimDefId))
        userFaberIssuerKey = userCLI.looper.run(getPublicKey(userCLI.agent.prover.wallet, faberClaimDefId))
        assert faberIssuerKey == userFaberIssuerKey

        do('show claim Transcript')
        assert userCLI.looper.run(getClaim(faberClaimDefId))

        # Accept acme
        do('load sample/acme-job-application.sovrin')
        syncInvite(be, do, userCLI, syncLinkOutWithEndpoint, aMap)
        acceptInvitation(be, do, userCLI, aMap,
                         syncedInviteAcceptedOutWithoutClaims)
        # Send claim
        do('show claim request Job-Application')
        do('set first_name to Alice')
        do('set last_name to Garcia')
        do('set phone_number to 123-45-6789')
        do('show claim request Job-Application')
        # Passing some args as None since they are not used in the method
        jobApplicationClaimSent(be, do, userCLI, aMap, None, None, None)
        # Request new available claims Job-Certificate
        jobCertClaimRequested(be, do, userCLI, None,
                              jobCertificateClaimMap, reqClaimOut1, None)

        acmeClaimDefId = ID(ClaimDefinitionKey('Job-Certificate', '0.2', aMap['target']))
        acmeIssuerKey = userCLI.looper.run(getPublicKey(acmeAgent.issuer.wallet, acmeClaimDefId))
        userAcmeIssuerKey = userCLI.looper.run(getPublicKey(userCLI.agent.prover.wallet, acmeClaimDefId))
        assert acmeIssuerKey == userAcmeIssuerKey

        do('show claim Job-Certificate')
        assert userCLI.looper.run(getClaim(acmeClaimDefId))

        # Accept thrift
        do('load sample/thrift-loan-application.sovrin')
        acceptInvitation(be, do, userCLI, tMap,
                         syncedInviteAcceptedOutWithoutClaims)
        # Send claims
        bankBasicClaimSent(be, do, userCLI, tMap, None)

        thriftAcmeIssuerKey = userCLI.looper.run(getPublicKey(thriftAgent.issuer.wallet, acmeClaimDefId))
        assert acmeIssuerKey == thriftAcmeIssuerKey
        passed = False
        try:
            bankKYCClaimSent(be, do, userCLI, tMap, None)
            passed = True
        except:
            thriftFaberIssuerKey = userCLI.looper.run(getPublicKey(thriftAgent.issuer.wallet, faberClaimDefId))
            assert faberIssuerKey == thriftFaberIssuerKey
        assert passed

    executeGstFlow("Alice", aliceCLI, aliceMap, be, connectedToTest, do, fMap,
                   aMap, jobCertificateClaimMap, newKeyringOut, reqClaimOut,
                   reqClaimOut1, syncLinkOutWithEndpoint,
                   syncedInviteAcceptedOutWithoutClaims, tMap,
                   transcriptClaimMap)

    aliceCLI.looper.runFor(3)

    executeGstFlow("Susan", susanCLI, susanMap, be, connectedToTest, do, fMap,
                   aMap, jobCertificateClaimMap, newKeyringOut, reqClaimOut,
                   reqClaimOut1, syncLinkOutWithEndpoint,
                   syncedInviteAcceptedOutWithoutClaims, tMap,
                   transcriptClaimMap)
