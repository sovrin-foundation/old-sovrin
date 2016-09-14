from _pytest.python import yield_fixture
from pytest import fixture

from plenum.common.looper import Looper
from plenum.common.startable import Status
from sovrin.agent.agent import Agent


@yield_fixture(scope="module")
def emptyLooper():
    with Looper() as l:
        yield l


@fixture(scope="module")
def agent():
    return Agent()


@fixture(scope="module")
def startedAgent(emptyLooper, agent):
    emptyLooper.add(agent)
    return agent


def testStartup(startedAgent, emptyLooper):
    assert startedAgent.isGoing() is True
    assert startedAgent.get_status() is Status.starting
    emptyLooper.runFor(.1)
    assert startedAgent.get_status() is Status.started


def testShutdown(startedAgent):
    startedAgent.stop()
    assert startedAgent.isGoing() is False
    assert startedAgent.get_status() is Status.stopped
