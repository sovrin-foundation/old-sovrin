import pytest
from plenum.common.txn import TYPE, NONCE

from plenum.common.types import f
from plenum.test.eventually import eventually
from sovrin.agent.agent import WalletedAgent
from sovrin.agent.msg_types import ACCEPT_INVITE
from sovrin.test.agent.conftest import checkAcceptInvitation

from sovrin.test.agent.helper import ensureAgentsConnected


def testFaberCreateLink(faberLinkAdded):
    pass


def testAliceLoadsInvitation(aliceInvitationLoaded):
    pass


def testAliceSyncsInvitationLink(aliceInvitationLinkSynced):
    pass


def testAliceAgentConnected(faberAdded, aliceAgentConnected):
    pass


def testFaberAdded(faberAdded):
    pass


def testAliceAcceptFaberInvitation(aliceAcceptedFaber):
    pass


def testAliceAcceptAcmeInvitation(acmeIsRunning, acmeNonceForAlice,
                         aliceIsRunning, emptyLooper):

    checkAcceptInvitation(emptyLooper,
                          acmeNonceForAlice,
                          aliceIsRunning,
                          acmeIsRunning)


@pytest.mark.skip("Not yet implemented")
def testAddClaimDef():
    raise NotImplementedError


@pytest.mark.skip("Not yet implemented")
def testAddIssuerKeys():
    raise NotImplementedError


def testMultipleAcceptance(aliceAcceptedFaber,
                           faberIsRunning,
                           faberLinkAdded,
                           faberAdded,
                           walletBuilder,
                           agentBuilder,
                           emptyLooper,
                           faberNonceForAlice):
    """
    For the test agent, Faber. Any invite nonce is acceptable.
    """
    faberAgent, _ = faberIsRunning
    assert len(faberAgent.wallet._links) == 1
    wallet = walletBuilder("Bob")
    otherAgent = agentBuilder(wallet)
    emptyLooper.add(otherAgent)

    checkAcceptInvitation(looper=emptyLooper,
                          nonce=faberNonceForAlice,
                          userAgent=otherAgent,
                          agentIsRunning=faberIsRunning)

    assert len(faberAgent.wallet._links) == 2


