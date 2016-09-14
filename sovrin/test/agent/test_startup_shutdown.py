from pytest import fixture
from plenum.common.startable import Status
from sovrin.agent.agent import Agent


@fixture()
def agent():
    return Agent()


@fixture()
def startedAgent(looper, agent):
    looper.add(agent)
    return agent


def testStartup(startedAgent, looper):
    # TODO: Why is OrientDB starting up???
    # TODO: Why is a node set startup up???
    assert startedAgent.isGoing() is True
    assert startedAgent.get_status() is Status.starting
    looper.runFor(.1)
    assert startedAgent.get_status() is Status.started


def testShutdown(startedAgent):
    startedAgent.stop()
    assert startedAgent.isGoing() is False
    assert startedAgent.get_status() is Status.stopped
