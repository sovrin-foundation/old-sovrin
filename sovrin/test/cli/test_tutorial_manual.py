import json
import logging

import re
import uuid

import pytest

from anoncreds.protocol.cred_def_secret_key import CredDefSecretKey
from anoncreds.protocol.issuer_secret_key import IssuerSecretKey
from plenum.common.exceptions import BlowUp
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


@pytest.mark.skip("Not yet implemented")
def testGettingStartedTutorialAgainstSandbox(newGuyCLI, be, do):
    be(newGuyCLI)
    do('connect test', within=3, expect="Connected to test")
    # TODO finish the entire set of steps


@pytest.fixture(scope="module")
def dangerousPrimes():
    """
    Hard-coded 'random' values are risky. Be careful only to use them in tests.
    """
    primes = {
        'Faber': adict(
            p=293672994294601538460023894424280657882248991230397936278278721070227017571960229217003029542172804429372056725385213277754094188540395813914384157706891192254644330822344382798277953427101186508616955910010980515685469918970002852483572038959508885430544201790234678752166995847136179984303153769450295059547,
            q=346129266351333939705152453226207841619953213173429444538411282110012597917194461301159547344552711191280095222396141806532237180979404522416636139654540172375588671099885266296364558380028106566373280517225387715617569246539059672383418036690030219091474419102674344117188434085686103371044898029209202469967),
        'Acme': adict(
            p=281510790031673293930276619603927743196841646256795847064219403348133278500884496133426719151371079182558480270299769814938220686172645009573713670952475703496783875912436235928500441867163946246219499572100554186255001186037971377948507437993345047481989113938038765221910989549806472045341069625389921020319,
            q=350024478159288302454189301319318317490551219044369889911215183350615705419868722006578530322735670686148639754382100627201250616926263978453441645496880232733783587241897694734699668219445029433427409979471473248066452686224760324273968172651114901114731981044897755380965310877273130485988045688817305189839),
        'a': adict(
            p=325893868236621235685694342853432128255662596084742701630702803797806397294325402126812757845898715987972301190236998259516672548030808077984482276443442275412976713276054747296981029661235027642854800917540051083248474400463038536670902017981223160527354520330405656489282463667701954783996896664500118936099,
            q=329899409150429298980613370321347023124241841562420222433597820015210005147824582997389773476164551065534815591959653484448297130127431301599544100359581695361882553029421713003518248069805870532619939187184623975486004399184422683818071105282880441021638024968277532668086638742939857932672778880586683619427),
        'b': adict(
            p=137625875492730856581920045634328472076227883212343498061881347876601486447638060405909079974596150020605200288974027885569380568142840230064337470172429862090037175028717471892027911829490200603632148340299661343748157395977746098316619165216971801180123723346384427006442977805419357117614536654841048327153,
            q=174253041093052798701667571910226261404941393093190977718291073968460639961528934463129759692190831567048894268291904325434607975497286179225006675346517650220247705979378238167561442959756275051080641831576510902583454881786632591919424557913638530560924594456691043111974653727236685189305891774598986798393),
        'c': adict(
            p=357389849121512584643721726419388406135160452970756835008680480758001408866242282133578003343373991135134728781213719599468354463325569361816295826511820663837329847190031645328446434960696872458759029613405263925650944945925366196751085870339897196326096345425833597399047277960837332356322350009300355607499,
            q=342079455850237921617548729688014020508617110965411358875830852105879462998168770280383363392240034400489921463325775158131883890744417222631439331458057973915480291350325381445669998803570049794284055237511890313226991412462187061975186009312420006599271275344978245567133314578077001632811263312103952490607),
        'd': adict(
            p=332615613455389134262091508687859712652487785774426521677776716415120896566798708679335127326530485021866445816872743433044403868096140973808942531141689070814490413391688989812008220219029542103111103626396452617240533570500332154989491647938292954575513848199909962636640482454800831961692930469571854354907,
            q=308592107685817602231521289897109126801421013999043087644348219937686528101839031931423133087064535989998981004405625767526881272361079929581656753389852529248408155631570924202880435723027240101431800967698020779108871957584102762385017863053675835932387107449861775836674272512681907749060484758533671391899),
        'e': adict(
            p=299947403925844187500938651923078192211173068457701788519569502067036416772701552518035669308026429038600822250748009608079143275300509204046811254826233303189173061188165140792583684166871078368539606776281631370482578625335542398889230742650595648099364536793795362672467496177008766400576214167133327422127,
            q=338791859680567544877003808885392999712107789322239943250126285690928766099592525792021210087168148701322452232431731541465353031400141525283798283235118972010570442479326924886391399557767009048408960299131181064189730811847288626602007418659461573545176465332056986208193992177961822340945854850951115953899),
        'f': adict(
            p=346463967541078361423745396498613784047214990828692629923000685322788515467207286932048730034039108353040399157798718865862699846702385221002706860869880265969986230487017456453294776067025680240648872227512660520427958147822622411074964199718344639053640014636041329357083262728740111561084581072529334579359,
            q=356385654235711166808832238039575439686451868129570558862901806461689671557975173255142533498556775321652602612476364330248259499421206424271465463626100925843087762335970701868056240428020816115196887042319104157965451421065925227180961377529734290600459373750559066073564810350818411406346239135247843024739),
        'g': adict(
            p=358742633929601263466592246013496459232656225007529536541515477364191843937865827547314619140514088534024397739591715210825395566978131361840478166093607458536769627096836259572559175327660795670259516897167801642240085980134037573389146904219327619628267242148829147884756904388534064759074235533350825536479,
            q=349393140856141611060192393340627395693094985673582812536975188666688404411176975766290003561641364655357291063489175690355045710913446385860640551672877974252828615339277336608379543961207976234518072905153537753244366094185059055928348220455738365435922087263335071249145948055208410359126009838518089186259),
        'h': adict(
            p=272350919439131518536668185723072482852926593554064019524369462343814526044511142103755498776619175126624938406364075917273451126568938668793961447374680502184029341737342100944414006903393754970664508203167093956633403100722241987837215822336410623517291152730072177767420285681479618823085013796383002848747,
            q=330425081558727167183816881221812849639549278034179184998296946366372434698517744313470524347706441922103884261563320081312205956446975847646990540428520632599603039481052004311129133768975937741073190081929985021145777509205395239068144377490406341441931166594773796692669520280184282602515003107867133236639),
    }
    return primes


# TODO: Remove this, dont need this anymore
@pytest.fixture(scope="module")
def forceSecrets(dangerousPrimes):

    dp = dangerousPrimes

    for k in dp.keys():
        dp[k].used = False

    pubkeys = {}

    def _generateIssuerSecretKey_INSECURE(self, claimDef):
        # if self.name not in dp:
        #     raise BlowUp("A test key pair for {} has not been created.".
        #                  format(self.name))
        # pair = dp[self.name]
        # if pair.used:
        #     raise BlowUp("A test key pair for {} has already been used.".
        #                  format(self.name))
        # pair = next(iter(dp.values()))
        pair = dp['Faber']
        csk = CredDefSecretKey(pair.p, pair.q)
        pair.used = True

        # TODO we shouldn't be storing claimdefsk, we are already storing
        # IssuerSecretKey which holds the ClaimDefSK
        sid = self.addClaimDefSk(str(csk))
        # TODO why are we using a uuid here? The uid should be the seqNo of
        # the pubkey in Sovrin
        isk = IssuerSecretKey(claimDef, csk, uid=str(uuid.uuid4()),
                              pubkey=pubkeys.get(claimDef.key))
        if not pubkeys.get(claimDef.key):
            pubkeys[claimDef.key] = isk.pubkey
        return isk

    # IssuerWallet._generateIssuerSecretKey = _generateIssuerSecretKey_INSECURE


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

    # Start Faber Agent and Acme Agent
    faberAgentPort = 5555
    acmeAgentPort = 6666
    fMap = faberMap(faberAgentPort)
    aMap = acmeMap(acmeAgentPort)

    agentParams = [
        (FaberAgent, faberCLI, "Faber College", faberAgentPort,
         buildFaberWallet),
        (AcmeAgent, acmeCLI, "Acme Corp", acmeAgentPort,
         buildAcmeWallet)
     ]

    for agentCls, agentCli, agentName, agentPort, buildAgentWalletFunc in \
            agentParams:
        # TODO: Remove None as credDefSeqNo and issuerKeySeqNo
        agentCls.getPassedArgs = lambda _: (agentPort,)
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
    # assert cred.issuerKeyId == faberIkSeqNo
    faberIssuerKeyAtAlice = aliceCLI.activeWallet.getIssuerPublicKey(
        seqNo=cred.issuerKeyId)

    # assert faberIssuerKeyAtAlice == faberIssuerKey
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

