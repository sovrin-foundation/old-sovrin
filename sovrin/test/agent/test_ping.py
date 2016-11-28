import pytest
from plenum.common.txn import TYPE, NONCE, IDENTIFIER

from plenum.common.types import f
from plenum.test.eventually import eventually
from sovrin.agent.msg_types import ACCEPT_INVITE, AVAIL_CLAIM_LIST

from sovrin.test.agent.helper import ensureAgentsConnected


def testPing(aliceAcceptedFaber, faberIsRunning, aliceAgent, emptyLooper):
    faberAgent, _ = faberIsRunning
    recvdPings = faberAgent.spylog.count(faberAgent._handlePing.__name__)
    recvdPongs = aliceAgent.spylog.count(aliceAgent._handlePong.__name__)
    aliceAgent.sendPing('Faber College')

    def chk():
        assert (recvdPings + 1) == faberAgent.spylog.count(
            faberAgent._handlePing.__name__)
        assert (recvdPongs + 1) == aliceAgent.spylog.count(
            aliceAgent._handlePong.__name__)

    emptyLooper.run(eventually(chk, retryWait=1, timeout=5))


