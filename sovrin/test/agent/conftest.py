import json
import os

import pytest

import sample
from plenum.common.txn import TYPE
from plenum.common.types import f
from plenum.common.util import randomString

from plenum.client.signer import SimpleSigner
from plenum.common.looper import Looper
from plenum.test.eventually import eventually
from plenum.test.helper import genHa, assertExp, assertFunc
from sovrin.agent.agent import WalletedAgent
from sovrin.client.client import Client
from sovrin.client.wallet.attribute import Attribute, LedgerStore
from sovrin.client.wallet.link import Link
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.txn import SPONSOR, NONCE, ENDPOINT
from sovrin.test.agent.acme import runAcme
from sovrin.test.agent.faber import runFaber
from sovrin.test.agent.helper import ensureAgentsConnected
from sovrin.test.helper import createNym, faberAddedClaimDefAndIssuerKeys, \
    addAttributeAndCheck, getStewardConnectedToPool
from sovrin.test.conftest import gennedTxnPoolNodeSet, updatedDomainTxnFile, \
    tdirWithDomainTxns, genesisTxns
from plenum.test.conftest import poolTxnStewardData, poolTxnStewardNames


@pytest.fixture(scope="module")
def emptyLooper():
    with Looper() as l:
        yield l


@pytest.fixture(scope="module")
def stewardAndWallet(gennedTxnPoolNodeSet, emptyLooper, tdirWithDomainTxns,
                     poolTxnStewardData):
    steward, wallet = getStewardConnectedToPool(emptyLooper,
                                                tdirWithDomainTxns,
                                                poolTxnStewardData)
    return steward, wallet


@pytest.fixture(scope="module")
def steward(stewardAndWallet):
    return stewardAndWallet[0]


@pytest.fixture(scope="module")
def stewardWallet(stewardAndWallet):
    return stewardAndWallet[1]


@pytest.fixture(scope="module")
def faberWallet():
    name = "FaberCollege"
    wallet = Wallet(name)
    wallet.addSigner(signer=SimpleSigner(
        seed=b'Faber000000000000000000000000000'))
    return wallet


@pytest.fixture(scope="module")
def walletBuilder():
    def _(name):
        wallet = Wallet(name)
        wallet.addSigner(signer=SimpleSigner())
        return wallet
    return _


@pytest.fixture(scope="module")
def aliceWallet(walletBuilder):
    return walletBuilder("Alice")


@pytest.fixture(scope="module")
def acmeWallet():
    name = "Acme"
    wallet = Wallet(name)
    return wallet


@pytest.fixture(scope="module")
def agentBuilder(tdirWithPoolTxns):
    def _(wallet, basedir=None):
        basedir = basedir or tdirWithPoolTxns
        _, port = genHa()
        _, clientPort = genHa()
        client = Client(randomString(6),
                        ha=("0.0.0.0", clientPort),
                        basedirpath=basedir)

        agent = WalletedAgent(name=wallet.name,
                              basedirpath=basedir,
                              client=client,
                              wallet=wallet,
                              port=port)

        return agent
    return _


@pytest.fixture(scope="module")
def aliceAgent(aliceWallet, agentBuilder):
    return agentBuilder(aliceWallet)


@pytest.fixture(scope="module")
def aliceIsRunning(emptyLooper, aliceAgent):
    emptyLooper.add(aliceAgent)
    return aliceAgent


@pytest.fixture(scope="module")
def aliceAgentConnected(gennedTxnPoolNodeSet,
                        aliceAgent,
                        aliceIsRunning,
                        emptyLooper):
    emptyLooper.run(
        eventually(
            assertFunc, aliceAgent.client.isReady))
    return aliceAgent


@pytest.fixture(scope="module")
def faberAgentPort():
    return genHa()[1]


@pytest.fixture(scope="module")
def acmeAgentPort():
    return genHa()[1]


@pytest.fixture(scope="module")
def faberAgent(tdirWithPoolTxns, faberAgentPort, faberWallet):
    agent = runFaber(faberWallet.name, faberWallet,
                     basedirpath=tdirWithPoolTxns,
                     port=faberAgentPort,
                     startRunning=False, bootstrap=False)
    return agent


@pytest.fixture(scope="module")
def faberAdded(gennedTxnPoolNodeSet,
               steward,
               stewardWallet,
               emptyLooper,
            faberAgentPort,
               faberAgent):

    attrib = createAgentAndAddEndpoint(emptyLooper, faberAgent.wallet.defaultId,
                                       faberAgentPort, steward, stewardWallet)
    return attrib


@pytest.fixture(scope="module")
def faberIsRunning(emptyLooper, tdirWithPoolTxns, faberWallet, faberAdded,
                   faberAgent):
    faber = faberAgent
    faber.addKeyIfNotAdded()
    faberWallet.pendSyncRequests()
    prepared = faberWallet.preparePending()
    faber.client.submitReqs(*prepared)
    # faber.bootstrap()
    emptyLooper.add(faber)

    cdSeqNo, iskSeqNo = faberAddedClaimDefAndIssuerKeys(emptyLooper, faber)
    faber._seqNos = {
        ("Transcript", "1.2"): (cdSeqNo, iskSeqNo)
    }

    return faber, faberWallet


@pytest.fixture(scope="module")
def acmeAgent(tdirWithPoolTxns, acmeAgentPort, acmeWallet):
    agent = runAcme(acmeWallet.name, acmeWallet,
                     basedirpath=tdirWithPoolTxns,
                     port=acmeAgentPort,
                     startRunning=False, bootstrap=False)
    agent.addKeyIfNotAdded()
    return agent


@pytest.fixture(scope="module")
def acmeAdded(gennedTxnPoolNodeSet,
               steward,
               stewardWallet,
               emptyLooper,
            acmeAgentPort,
               acmeAgent):
    attrib = createAgentAndAddEndpoint(emptyLooper, acmeAgent.wallet.defaultId,
                                       acmeAgentPort, steward, stewardWallet)
    return attrib


@pytest.fixture(scope="module")
def acmeIsRunning(emptyLooper, tdirWithPoolTxns, acmeWallet, acmeAgent,
                  acmeAdded):
    acme = acmeAgent
    acmeWallet.pendSyncRequests()
    prepared = acmeWallet.preparePending()
    acme.client.submitReqs(*prepared)
    emptyLooper.add(acme)
    return acme, acmeWallet


# TODO: Rename it, not clear whether link is added to which wallet and
# who is adding
@pytest.fixture(scope="module")
def faberLinkAdded(faberIsRunning):
    # DEPR
    # faber, wallet = faberIsRunning
    # idr = wallet.defaultId
    # link = Link("Alice", idr, nonce="b1134a647eb818069c089e7694f63e6d")
    # wallet.addLink(link)
    # assert wallet.getMatchingLinks("Alice")
    # return link
    pass


@pytest.fixture(scope="module")
def acmeLinkAdded(acmeIsRunning):
    # DEPR
    # acme, wallet = acmeIsRunning
    # idr = wallet.defaultId
    # link = Link("Acme", idr, nonce="57fbf9dc8c8e6acde33de98c6d747b28c")
    # # TODO rename to addLink
    # wallet.addLink(link)
    # assert wallet.getMatchingLinks("Acme")
    # return link
    pass


@pytest.fixture(scope="module")
def faberNonceForAlice():
    return 'b1134a647eb818069c089e7694f63e6d'


@pytest.fixture(scope="module")
def acmeNonceForAlice():
    return '57fbf9dc8c8e6acde33de98c6d747b28c'


@pytest.fixture(scope="module")
def aliceAcceptedFaber(faberIsRunning, faberNonceForAlice, faberAdded,
                       aliceIsRunning, emptyLooper,
                       aliceFaberInvitationLoaded,
                       aliceFaberInvitationLinkSynced):
    """
    Faber creates a Link object, generates a link invitation file.
    Start FaberAgent
    Start AliceAgent and send a ACCEPT_INVITE to FaberAgent.
    """

    checkAcceptInvitation(emptyLooper,
                          faberNonceForAlice,
                          aliceIsRunning,
                          faberIsRunning,
                          linkName='Faber College')


@pytest.fixture(scope="module")
def faberInvitation():
    return getInvitationFile('faber-invitation.sovrin')


@pytest.fixture(scope="module")
def acmeInvitation():
    return getInvitationFile('acme-job-application.sovrin')


@pytest.fixture(scope="module")
def aliceFaberInvitationLoaded(aliceAgent, faberInvitation):
    link = agentInvitationLoaded(aliceAgent, faberInvitation)
    assert link.name == 'Faber College'
    return link


@pytest.fixture(scope="module")
def aliceFaberInvitationLinkSynced(aliceFaberInvitationLoaded,
                              aliceAgentConnected,
                              aliceAgent: WalletedAgent,
                              emptyLooper,
                              faberAdded
                              ):
    agentInvitationLinkSynced(aliceAgent, aliceFaberInvitationLoaded.name,
                              emptyLooper)


@pytest.fixture(scope="module")
def aliceAcmeInvitationLoaded(aliceAgent, acmeInvitation):
    link = agentInvitationLoaded(aliceAgent, acmeInvitation)
    assert link.name == 'Acme Corp'
    return link


@pytest.fixture(scope="module")
def aliceAcmeInvitationLinkSynced(aliceAcmeInvitationLoaded,
                              aliceAgentConnected,
                              aliceAgent: WalletedAgent,
                              emptyLooper,
                            acmeAdded
                              ):
    agentInvitationLinkSynced(aliceAgent, aliceAcmeInvitationLoaded.name,
                              emptyLooper)


@pytest.fixture(scope="module")
def aliceAcceptedAcme(acmeIsRunning, acmeNonceForAlice, acmeAdded,
                       aliceIsRunning, emptyLooper,
                      aliceAcmeInvitationLinkSynced):
    """
    Faber creates a Link object, generates a link invitation file.
    Start FaberAgent
    Start AliceAgent and send a ACCEPT_INVITE to FaberAgent.
    """

    checkAcceptInvitation(emptyLooper,
                          acmeNonceForAlice,
                          aliceIsRunning,
                          acmeIsRunning,
                          linkName='Acme Corp')


def checkAcceptInvitation(emptyLooper,
                          nonce,
                          userAgent: WalletedAgent,
                          agentIsRunning,
                          linkName):
    """
    Assumes link identified by linkName is already created
    """
    assert nonce
    agent, awallet = agentIsRunning
    a = agent  # type: WalletedAgent

    userAgent.connectTo(linkName)
    ensureAgentsConnected(emptyLooper, userAgent, agent)

    userAgent.acceptInvitation(linkName)

    internalId = a.getInternalIdByInvitedNonce(nonce)

    def chk():
        link = a.wallet.getLinkByInternalId(internalId)
        assert link
        # if not link:
        #     raise RuntimeError("Link not found for internal ID {}".
        #                        format(internalId))
        assert link.remoteIdentifier == userAgent.wallet.defaultId
        assert link.remoteEndPoint[1] == userAgent.endpoint.ha[1]

        emptyLooper.run(eventually(chk))


def createAgentAndAddEndpoint(looper, agentNym, agentPort, steward,
                              stewardWallet):
    createNym(looper,
              agentNym,
              steward,
              stewardWallet,
              role=SPONSOR)
    ep = '127.0.0.1:{}'.format(agentPort)
    attributeData = json.dumps({ENDPOINT: ep})

    # TODO Faber Agent should be doing this!
    attrib = Attribute(name='{}_endpoint'.format(agentNym),
                       origin=stewardWallet.defaultId,
                       value=attributeData,
                       dest=agentNym,
                       ledgerStore=LedgerStore.RAW)
    addAttributeAndCheck(looper, steward, stewardWallet, attrib)
    return attrib


def getInvitationFile(fileName):
    sampleDir = os.path.dirname(sample.__file__)
    return os.path.join(sampleDir, fileName)


def agentInvitationLoaded(agent, invitaition):
    link = agent.loadInvitationFile(invitaition)
    assert link
    return link


def agentInvitationLinkSynced(agent,
                              linkName,
                              looper):
    done = False

    def cb(reply, err):
        nonlocal done
        assert reply
        assert not err
        done = True

    def checkDone():
        assert done

    agent.sync(linkName, cb)
    looper.run(eventually(checkDone))

    link = agent.wallet.getLink(linkName, required=True)
    assert link
    ep = link.remoteEndPoint
    assert ep
    assert len(ep) == 2
