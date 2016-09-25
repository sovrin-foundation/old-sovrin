import pytest
from sovrin.client.wallet.link_invitation import Link
from sovrin.test.agent.helper import connectAgents, ensureAgentsConnected


@pytest.fixture(scope="module")
def faberLinkAdded(faberIsRunning):
    faber, wallet = faberIsRunning
    idr = wallet.defaultId
    link = Link("Alice", idr, wallet._getIdData().signer.verkey)
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


def testAddClaimDef():
    pass


def testAddIssuerKeys():
    pass
