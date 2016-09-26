from plenum.test.eventually import eventually
from plenum.test.helper import checkRemoteExists, CONNECTED
from raet.road.estating import RemoteEstate


def connectAgents(agent1, agent2):
    e1 = agent1.endpoint
    e2 = agent2.endpoint
    remote = RemoteEstate(stack=e1, ha=e2.ha)
    e1.addRemote(remote)
    # updates the store time so the join timer is accurate
    e1.updateStamp()
    e1.join(uid=remote.uid, cascade=True, timeout=30)


def ensureAgentsConnected(looper, agent1, agent2):
    connectAgents(agent1, agent2)
    e1 = agent1.endpoint
    e2 = agent2.endpoint
    looper.run(eventually(checkRemoteExists, e1, e2.name, CONNECTED,
                          timeout=10))
    looper.run(eventually(checkRemoteExists, e2, e1.name, CONNECTED,
                          timeout=10))
