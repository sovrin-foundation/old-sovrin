import pytest
from plenum.common.txn import TYPE, NONCE

from plenum.common.types import f
from plenum.test.eventually import eventually
from sovrin.agent.agent import WalletedAgent
from sovrin.agent.msg_types import ACCEPT_INVITE

from sovrin.test.agent.helper import ensureAgentsConnected


def testFaberCreateLink(faberLinkAdded):
    pass


def checkAcceptInvitation(looper,
                          nonce,
                          userAgent: WalletedAgent,
                          agentIsRunning):
    assert nonce
    agent, awallet = agentIsRunning
    a = agent  # type: WalletedAgent
    ensureAgentsConnected(looper, userAgent, agent)
    msg = {
        TYPE: ACCEPT_INVITE,
        f.IDENTIFIER.nm: userAgent.wallet.defaultId,
        NONCE: nonce,
    }
    sig = userAgent.wallet.signMsg(msg)
    msg[f.SIG.nm] = sig
    userAgent.sendMessage(msg, agent.endpoint.name)

    internalId = a.getInternalIdByInvitedNonce(nonce)

    def chk():
        link = a.wallet.getLinkByInternalId(internalId)
        assert link
        # if not link:
        #     raise RuntimeError("Link not found for internal ID {}".
        #                        format(internalId))
        assert link.remoteIdentifier == userAgent.wallet.defaultId
        assert link.remoteEndPoint[1] == userAgent.endpoint.ha[1]

    looper.run(eventually(chk))


@pytest.fixture(scope="module")
def faberNonceForAlice():
    return 'b1134a647eb818069c089e7694f63e6d'


@pytest.fixture(scope="module")
def acmeNonceForAlice():
    return '57fbf9dc8c8e6acde33de98c6d747b28c'


@pytest.fixture(scope="module")
def aliceAcceptedFaber(faberIsRunning, faberNonceForAlice, faberAdded,
                         aliceIsRunning, emptyLooper):
    """
    Faber creates a Link object, generates a link invitation file.
    Start FaberAgent
    Start AliceAgent and send a ACCEPT_INVITE to FaberAgent.
    """

    checkAcceptInvitation(emptyLooper,
                          faberNonceForAlice,
                          aliceIsRunning,
                          faberIsRunning)


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


