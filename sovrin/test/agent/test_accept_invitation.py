import pytest
from plenum.common.txn import TYPE, NONCE

from plenum.common.types import f
from plenum.test.eventually import eventually
from sovrin.agent.msg_types import ACCEPT_INVITE
from sovrin.test.agent.helper import ensureAgentsConnected


def testFaberCreateLink(faberLinkAdded):
    pass


def checkAcceptInvitation(emptyLooper, agentLinkAdded, userIsRunning,
                          agentIsRunning):

    agent, awallet = agentIsRunning
    user, uwallet = userIsRunning
    ensureAgentsConnected(emptyLooper, user, agent)
    msg = {
        TYPE: ACCEPT_INVITE,
        f.IDENTIFIER.nm: uwallet.defaultId,
        NONCE: agentLinkAdded.nonce,
    }
    sig = uwallet.signMsg(msg)
    msg[f.SIG.nm] = sig
    user.sendMessage(msg, agent.endpoint.name)

    def chk():
        assert agentLinkAdded.remoteIdentifier == uwallet.defaultId
        assert agentLinkAdded.remoteEndPoint[1] == user.endpoint.ha[1]
        # TODO: need to check remote identifier

    emptyLooper.run(eventually(chk))


def testAliceAcceptFaberInvitation(faberIsRunning, faberLinkAdded, faberAdded,
                         aliceIsRunning, emptyLooper):
    """
    Faber creates a Link object, generates a link invitation file.
    Start FaberAgent
    Start AliceAgent and send a ACCEPT_INVITE to FaberAgent.
    """

    checkAcceptInvitation(emptyLooper, faberLinkAdded, aliceIsRunning,
                          faberIsRunning)


def testAliceAcceptAcmeInvitation(acmeIsRunning, acmeLinkAdded, acmeAdded,
                         aliceIsRunning, emptyLooper):

    checkAcceptInvitation(emptyLooper, acmeLinkAdded, aliceIsRunning,
                          acmeIsRunning)

@pytest.mark.skip("Not yet implemented")
def testAddClaimDef():
    raise NotImplementedError


@pytest.mark.skip("Not yet implemented")
def testAddIssuerKeys():
    raise NotImplementedError
