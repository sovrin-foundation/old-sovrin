import pytest
from plenum.common.types import f
from plenum.test.eventually import eventually
from sovrin.agent.msg_types import ACCEPT_INVITE
from sovrin.client.wallet.link_invitation import Link
from sovrin.common.util import getNonce
from sovrin.test.agent.helper import connectAgents, ensureAgentsConnected


@pytest.fixture(scope="module")
def faberLinkAdded(faberIsRunning):
    faber, wallet = faberIsRunning
    idr = wallet.defaultId
    link = Link("Alice", idr, nonce=getNonce(7))
    # TODO rename to addLink
    wallet.addLinkInvitation(link)
    assert wallet.getMatchingLinkInvitations("Alice")
    return link


def testFaberCreateLink(faberLinkAdded):
    pass


def testAcceptInvitation(faberIsRunning, faberLinkAdded, faberAdded,
                         aliceIsRunning, emptyLooper):
    """
    Faber creates a Link object, generates a link invitation file.
    Start FaberAgent
    Start AliceAgent and send a ACCEPT_INVITE to FaberAgent.
    """
    faber, fwallet = faberIsRunning
    alice, awallet = aliceIsRunning
    ensureAgentsConnected(emptyLooper, alice, faber)
    msg = {
        'type': ACCEPT_INVITE,
        f.IDENTIFIER.nm: awallet.defaultId,
        'nonce': faberLinkAdded.nonce,
        f.SIG.nm: 'dsd'
    }
    alice.sendMessage(msg, faber.endpoint.name)

    def chk():
        assert faberLinkAdded.remoteIdentifier == awallet.defaultId
        assert faberLinkAdded.remoteEndPoint[1] == alice.endpoint.ha[1]
        # TODO: need to check remote identifier

    emptyLooper.run(eventually(chk))


def testAddClaimDef():
    pass


def testAddIssuerKeys():
    pass
