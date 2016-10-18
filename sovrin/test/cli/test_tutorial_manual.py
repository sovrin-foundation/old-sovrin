import json
import logging

import re
import uuid

import pytest
import sys

from anoncreds.protocol.cred_def_secret_key import CredDefSecretKey
from anoncreds.protocol.issuer_secret_key import IssuerSecretKey
from plenum.common.port_dispenser import genHa
from plenum.common.util import adict
from plenum.test import eventually

from sovrin.agent.agent import runAgent
from sovrin.client.wallet.issuer_wallet import IssuerWallet
from sovrin.common.setup_util import Setup
from sovrin.common.txn import ENDPOINT
from sovrin.test.agent.acme import AcmeAgent
from sovrin.test.agent.faber import FaberAgent
from sovrin.test.agent.helper import buildFaberWallet, buildAcmeWallet
from sovrin.test.agent.thrift import ThriftAgent
from sovrin.test.cli.conftest import faberMap, acmeMap
from sovrin.test.cli.helper import newCLI

# noinspection PyUnresolvedReferences
from sovrin.test.cli.test_tutorial import poolNodesStarted, faberCLI, \
    faberCli as createFaberCli, aliceCli as createAliceCli, acmeCLI, \
    acmeCli as createAcmeCli, syncInvite, acceptInvitation, \
    aliceRequestedTranscriptClaim, jobApplicationClaimSent

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


def testGettingStartedTutorialAgainstSandbox(newGuyCLI, be, do):
    be(newGuyCLI)
    do('connect test', within=3, expect="Connected to test")
    # TODO finish the entire set of steps


@pytest.fixture(scope="module")
def forceSecrets(staticPrimes):

    primes = {
        'Faber': adict(
            p=293672994294601538460023894424280657882248991230397936278278721070227017571960229217003029542172804429372056725385213277754094188540395813914384157706891192254644330822344382798277953427101186508616955910010980515685469918970002852483572038959508885430544201790234678752166995847136179984303153769450295059547,
            q=346129266351333939705152453226207841619953213173429444538411282110012597917194461301159547344552711191280095222396141806532237180979404522416636139654540172375588671099885266296364558380028106566373280517225387715617569246539059672383418036690030219091474419102674344117188434085686103371044898029209202469967),
        'Acme': adict(
            p=281510790031673293930276619603927743196841646256795847064219403348133278500884496133426719151371079182558480270299769814938220686172645009573713670952475703496783875912436235928500441867163946246219499572100554186255001186037971377948507437993345047481989113938038765221910989549806472045341069625389921020319,
            q=350024478159288302454189301319318317490551219044369889911215183350615705419868722006578530322735670686148639754382100627201250616926263978453441645496880232733783587241897694734699668219445029433427409979471473248066452686224760324273968172651114901114731981044897755380965310877273130485988045688817305189839),
        '?': adict(
            p=325893868236621235685694342853432128255662596084742701630702803797806397294325402126812757845898715987972301190236998259516672548030808077984482276443442275412976713276054747296981029661235027642854800917540051083248474400463038536670902017981223160527354520330405656489282463667701954783996896664500118936099,
            q=329899409150429298980613370321347023124241841562420222433597820015210005147824582997389773476164551065534815591959653484448297130127431301599544100359581695361882553029421713003518248069805870532619939187184623975486004399184422683818071105282880441021638024968277532668086638742939857932672778880586683619427),
    }
    csk = CredDefSecretKey(*staticPrimes.get("prime1"))

    def _generateIssuerSecretKey_INSECURE(self, claimDef):
        pair = primes[self.name]
        csk = CredDefSecretKey(pair.p, pair.q)
        # TODO we shouldn't be storing claimdefsk, we are already storing IssuerSecretKey which holds the ClaimDefSK
        sid = self.addClaimDefSk(str(csk))
        # TODO why are we using a uuid here? The uid should be the seqNo of the pubkey in Sovrin
        isk = IssuerSecretKey(claimDef, csk, uid=str(uuid.uuid4()))
        return isk

    IssuerWallet._generateIssuerSecretKey = _generateIssuerSecretKey_INSECURE


def testManual(forceSecrets, do, be, poolNodesStarted, poolTxnStewardData, philCLI,
               connectedToTest, nymAddedOut, attrAddedOut, faberCLI,
               credDefAdded, issuerKeyAdded, aliceCLI, newKeyringOut, aliceMap,
               acmeCLI, tdir, syncLinkOutWithEndpoint,
               syncedInviteAcceptedOutWithoutClaims, transcriptClaimMap,
               reqClaimOut):

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
    for nym, ep in [('FuN98eH2eZybECWkofW6A9BKJxxnTatBCopfUiNxo6ZB', '127.0.0.1:5555'),
                    ('7YD5NKn3P4wVJLesAmA1rr7sLPqW9mR1nhFdKD518k21', '127.0.0.1:6666'),
                    ('9jegUr9vAMqoqQQUEAiCBYNQDnUbTktQY9nNspxfasZW', '127.0.0.1:7777')]:
        m = {'target': nym, 'endpoint': json.dumps({ENDPOINT: ep})}
        do('send NYM dest={target} role=SPONSOR',
           within=3, expect=nymAddedOut, mapper=m)
        do('send ATTRIB dest={target} raw={endpoint}', within=3,
           expect=attrAddedOut, mapper=m)

    # Start Faber cli and add cred def and issuer key
    createFaberCli(be, do, faberCLI)
    be(faberCLI)
    do('connect test', within=3, expect=connectedToTest)
    do('send CRED_DEF name=Transcript '
       'version=1.2 type=CL '
       'keys=student_name,ssn,degree,'
       'year,status',
       within=3, expect=credDefAdded)
    faberCdSeqNo = getSeqNoFromCliOutput(faberCLI)
    do('send ISSUER_KEY ref={seqNo}', within=3, expect=issuerKeyAdded,
       mapper=dict(seqNo=faberCdSeqNo))
    faberIkSeqNo = int(getSeqNoFromCliOutput(faberCLI))

    faberIssuerKey = faberCLI.activeWallet.getIssuerPublicKey(
        seqNo=faberIkSeqNo)

    # Start Acme cli and add cred def and issuer key
    createAcmeCli(be, do, acmeCLI)
    be(acmeCLI)
    do('connect test', within=3, expect=connectedToTest)
    do('send CRED_DEF name=Job-Certificate '
       'version=0.2 type=CL keys=first_name,'
       'last_name,employee_status,experience,'
       'salary_bracket', within=3, expect=credDefAdded)
    acmeCdSeqNo = getSeqNoFromCliOutput(acmeCLI)
    do(
        'send ISSUER_KEY ref={seqNo}', within=3, expect=issuerKeyAdded,
        mapper=dict(seqNo=acmeCdSeqNo))
    acmeIkSeqNo = getSeqNoFromCliOutput(acmeCLI)

    # Start Faber Agent and Acme Agent
    faberAgentPort = 5555
    acmeAgentPort = 6666
    fMap = faberMap(faberAgentPort)
    aMap = acmeMap(acmeAgentPort)

    agentParams = [
        (FaberAgent, faberCLI, "Faber College", faberAgentPort,
         faberCdSeqNo, faberIkSeqNo, buildFaberWallet),
        (AcmeAgent, acmeCLI, "Acme Corp", acmeAgentPort,
         acmeCdSeqNo, acmeIkSeqNo, buildAcmeWallet)
     ]

    for agentCls, agentCli, agentName, agentPort, agentCdSeqNo, agentIkSeqNo, \
            buildAgentWalletFunc in agentParams:
        agentCls.getPassedArgs = lambda _: (agentPort,
                                            int(agentCdSeqNo),
                                            int(agentIkSeqNo))
        agent = runAgent(agentCls, agentName, buildAgentWalletFunc(), tdir,
                         agentPort, False, True)
        agentCli.looper.add(agent)

    # Start Alice cli
    createAliceCli(be, do, aliceCLI, newKeyringOut, aliceMap)
    be(aliceCLI)
    do('connect test', within=3, expect=connectedToTest)

    # Accept faber
    do('load sample/faber-invitation.sovrin')
    syncInvite(be, do, aliceCLI, syncLinkOutWithEndpoint, fMap)
    do('show link faber')
    acceptInvitation(be, do, aliceCLI, fMap,
                     syncedInviteAcceptedOutWithoutClaims)

    # Request claim
    do('show claim Transcript')
    aliceRequestedTranscriptClaim(be, do, aliceCLI, transcriptClaimMap,
                                  reqClaimOut,
                                  None,  # Passing None since its not used
                                  None)  # Passing None since its not used
    do('show claim Transcript')
    # TODO
    # do('show claim Transcript verbose')
    cred = aliceCLI.activeWallet.getCredential('Faber College Transcript 1.2')
    assert cred.issuerKeyId == faberIkSeqNo
    faberIssuerKeyAtAlice = faberCLI.activeWallet.getIssuerPublicKey(
        seqNo=cred.issuerKeyId)

    assert faberIssuerKeyAtAlice == faberIssuerKey
    # Accept acme
    do('load sample/acme-job-application.sovrin')
    syncInvite(be, do, aliceCLI, syncLinkOutWithEndpoint, aMap)
    acceptInvitation(be, do, aliceCLI, aMap,
                     syncedInviteAcceptedOutWithoutClaims)

    # Send claim
    do('show claim request Job-Application')
    do('set first_name to Alice')
    do('set last_name to Garcia')
    do('set phone_number to 123-45-6789')
    do('show claim request Job-Application')
    # Passing some args as None since they are not used in the method
    jobApplicationClaimSent(be, do, aliceCLI, aMap, None, None, None)

