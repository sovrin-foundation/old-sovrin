import pytest
from plenum.common.txn import TYPE, NONCE

from plenum.common.types import f
from plenum.test.eventually import eventually
from sovrin.agent.msg_types import ACCEPT_INVITE
from sovrin.test.agent.helper import ensureAgentsConnected


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
        TYPE: ACCEPT_INVITE,
        f.IDENTIFIER.nm: awallet.defaultId,
        NONCE: faberLinkAdded.nonce,
    }
    sig = awallet.signMsg(msg)
    msg[f.SIG.nm] = sig
    alice.sendMessage(msg, faber.endpoint.name)

    def chk():
        assert faberLinkAdded.remoteIdentifier == awallet.defaultId
        assert faberLinkAdded.remoteEndPoint[1] == alice.endpoint.ha[1]
        # TODO: need to check remote identifier

    emptyLooper.run(eventually(chk))


@pytest.mark.skip("Not yet implemented")
def testAddClaimDef():
    raise NotImplementedError


@pytest.mark.skip("Not yet implemented")
def testAddIssuerKeys():
    raise NotImplementedError
