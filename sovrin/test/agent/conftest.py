from plenum.common.port_dispenser import genHa
from plenum.common.signer_did import DidSigner

from sovrin.common.strict_types import strict_types
from sovrin.test.agent.test_walleted_agent import TestWalletedAgent

strict_types.defaultShouldCheck = True

# def pytest_configure(config):
#     setattr(sys, '_called_from_test', True)
#
#
# def pytest_unconfigure(config):
#     delattr(sys, '_called_from_test')
#
#
import json
import os

import pytest

import sample
from plenum.common.looper import Looper
from plenum.common.util import randomString
from plenum.common.eventually import eventually
from plenum.test.helper import assertFunc
from sovrin.agent.agent import runAgent
from sovrin.agent.agent import WalletedAgent
from sovrin.client.wallet.attribute import Attribute, LedgerStore
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.txn import SPONSOR, ENDPOINT
from sovrin.test.agent.acme import createAcme
from sovrin.test.agent.faber import createFaber
from sovrin.test.agent.helper import ensureAgentsConnected, buildFaberWallet, \
    buildAcmeWallet, buildThriftWallet
from sovrin.test.agent.thrift import createThrift
from sovrin.test.helper import createNym, addAttributeAndCheck, TestClient

# noinspection PyUnresolvedReferences
from sovrin.test.conftest import nodeSet, updatedDomainTxnFile, \
    genesisTxns

# noinspection PyUnresolvedReferences
from plenum.test.conftest import poolTxnStewardData, poolTxnStewardNames


@pytest.fixture(scope="module")
def emptyLooper():
    with Looper() as l:
        yield l


@pytest.fixture(scope="module")
def walletBuilder():
    def _(name):
        wallet = Wallet(name)
        wallet.addIdentifier(signer=DidSigner())
        return wallet
    return _


@pytest.fixture(scope="module")
def aliceWallet(walletBuilder):
    return walletBuilder("Alice")


@pytest.fixture(scope="module")
def faberWallet():
    return buildFaberWallet()


@pytest.fixture(scope="module")
def acmeWallet():
    return buildAcmeWallet()


@pytest.fixture(scope="module")
def thriftWallet():
    return buildThriftWallet()


@pytest.fixture(scope="module")
def agentBuilder(tdirWithPoolTxns):
    def _(wallet, basedir=None):
        basedir = basedir or tdirWithPoolTxns
        _, port = genHa()
        _, clientPort = genHa()
        client = TestClient(randomString(6),
                            ha=("0.0.0.0", clientPort),
                            basedirpath=basedir)

        agent = TestWalletedAgent(name=wallet.name,
                                  basedirpath=basedir,
                                  client=client,
                                  wallet=wallet,
                                  port=port)

        return agent
    return _


@pytest.fixture(scope="module")
def aliceAgent(aliceWallet, agentBuilder):
    agent = agentBuilder(aliceWallet)
    return agent


@pytest.fixture(scope="module")
def aliceIsRunning(emptyLooper, aliceAgent):
    emptyLooper.add(aliceAgent)
    return aliceAgent


@pytest.fixture(scope="module")
def aliceAgentConnected(nodeSet,
                        aliceAgent,
                        aliceIsRunning,
                        emptyLooper):
    emptyLooper.run(
        eventually(
            assertFunc, aliceAgent.client.isReady))
    return aliceAgent


@pytest.fixture(scope="module")
def agentIpAddress():
    return "127.0.0.1"


@pytest.fixture(scope="module")
def faberAgentPort():
    return genHa()[1]


@pytest.fixture(scope="module")
def acmeAgentPort():
    return genHa()[1]


@pytest.fixture(scope="module")
def thriftAgentPort():
    return genHa()[1]


@pytest.fixture(scope="module")
def faberAgent(tdirWithPoolTxns, faberAgentPort, faberWallet):
    return createFaber(faberWallet.name, faberWallet,
                       basedirpath=tdirWithPoolTxns,
                       port=faberAgentPort)


@pytest.fixture(scope="module")
def faberAdded(nodeSet,
               steward,
               stewardWallet,
               emptyLooper,
               faberAgentPort,
               faberAgent):
    attrib = createAgentAndAddEndpoint(emptyLooper,
                                       faberAgent.wallet.defaultId,
                                       faberAgent.wallet.getVerkey(),
                                       faberAgentPort,
                                       steward,
                                       stewardWallet)
    return attrib


@pytest.fixture(scope="module")
def faberIsRunning(emptyLooper, tdirWithPoolTxns, faberWallet,
                   faberAgent, faberAdded):
    faber = faberAgent
    faberWallet.pendSyncRequests()
    prepared = faberWallet.preparePending()
    faber.client.submitReqs(*prepared)

    runAgent(faber, emptyLooper)

    return faber, faberWallet


@pytest.fixture(scope="module")
def acmeAgent(tdirWithPoolTxns, acmeAgentPort, acmeWallet):
    return createAcme(acmeWallet.name, acmeWallet,
                      basedirpath=tdirWithPoolTxns,
                      port=acmeAgentPort)


@pytest.fixture(scope="module")
def acmeAdded(nodeSet,
              steward,
              stewardWallet,
              emptyLooper,
              acmeAgentPort,
              acmeAgent):
    attrib = createAgentAndAddEndpoint(emptyLooper,
                                       acmeAgent.wallet.defaultId,
                                       acmeAgent.wallet.getVerkey(),
                                       acmeAgentPort,
                                       steward,
                                       stewardWallet)
    return attrib


@pytest.fixture(scope="module")
def acmeIsRunning(emptyLooper, tdirWithPoolTxns, acmeWallet, acmeAgent,
                  acmeAdded):
    acme = acmeAgent
    acmeWallet.pendSyncRequests()
    prepared = acmeWallet.preparePending()
    acme.client.submitReqs(*prepared)

    runAgent(acme, emptyLooper)

    return acme, acmeWallet


@pytest.fixture(scope="module")
def thriftAgent(tdirWithPoolTxns, thriftAgentPort, thriftWallet):
    return createThrift(thriftWallet.name, thriftWallet,
                        basedirpath=tdirWithPoolTxns,
                        port=thriftAgentPort)


@pytest.fixture(scope="module")
def thriftIsRunning(emptyLooper, tdirWithPoolTxns, thriftWallet,
                    thriftAgent, thriftAdded):
    thrift = thriftAgent
    thriftWallet.pendSyncRequests()
    prepared = thriftWallet.preparePending()
    thrift.client.submitReqs(*prepared)

    runAgent(thrift, emptyLooper)

    return thrift, thriftWallet


# TODO: Rename it, not clear whether link is added to which wallet and
# who is adding
@pytest.fixture(scope="module")
def faberLinkAdded(faberIsRunning):
    pass


@pytest.fixture(scope="module")
def acmeLinkAdded(acmeIsRunning):
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
                                   faberAdded):
    agentInvitationLinkSynced(aliceAgent,
                              aliceFaberInvitationLoaded.name,
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
                                  acmeAdded):
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
                          inviteeAgent: WalletedAgent,
                          inviterAgentAndWallet,
                          linkName):
    """
    Assumes link identified by linkName is already created
    """
    assert nonce
    inviterAgent, inviterWallet = inviterAgentAndWallet # type: WalletedAgent, Wallet

    inviteeWallet = inviteeAgent.wallet
    inviteeAgent.connectTo(linkName)
    ensureAgentsConnected(emptyLooper, inviteeAgent, inviterAgent)

    inviteeAgent.acceptInvitation(linkName)
    inviteeAcceptanceId = inviteeWallet.getLink(linkName,
                                                required=True).localIdentifier
    internalId = inviterAgent.getInternalIdByInvitedNonce(nonce)

    def chk():
        link = inviterWallet.getLinkByInternalId(internalId)
        assert link
        # if not link:
        #     raise RuntimeError("Link not found for internal ID {}".
        #                        format(internalId))
        # TODO: Get link from invitee wallet to check.
        assert link.remoteIdentifier == inviteeAcceptanceId
        assert link.remoteEndPoint[1] == inviteeAgent.endpoint.ha[1]

    emptyLooper.run(eventually(chk))


def createAgentAndAddEndpoint(looper, agentNym, agentVerkey, agentPort, steward,
                              stewardWallet):
    createNym(looper,
              agentNym,
              steward,
              stewardWallet,
              role=SPONSOR,
              verkey=agentVerkey)
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


def agentInvitationLoaded(agent, invitation):
    link = agent.loadInvitationFile(invitation)
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
        assert done, 'never got reply for agent link sync'

    agent.sync(linkName, cb)
    looper.run(eventually(checkDone))

    link = agent.wallet.getLink(linkName, required=True)
    assert link
    ep = link.remoteEndPoint
    assert ep
    assert len(ep) == 2
