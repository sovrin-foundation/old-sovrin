from plenum.common.eventually import eventually


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


