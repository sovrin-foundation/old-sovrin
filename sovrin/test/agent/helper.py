import argparse

import sys
from plenum.test.eventually import eventually
from plenum.test.helper import checkRemoteExists, CONNECTED, logger
from raet.road.estating import RemoteEstate


def connectAgents(agent1, agent2):
    e1 = agent1.endpoint
    e2 = agent2.endpoint
    e1.connectTo(e2.ha)


def ensureAgentsConnected(looper, agent1, agent2):
    connectAgents(agent1, agent2)
    e1 = agent1.endpoint
    e2 = agent2.endpoint
    looper.run(eventually(checkRemoteExists, e1, e2.name, CONNECTED,
                          timeout=10))
    looper.run(eventually(checkRemoteExists, e2, e1.name, CONNECTED,
                          timeout=10))


def getAgentCmdLineParams():
    if sys.stdin.isatty():
        parser = argparse.ArgumentParser(
            description="Starts agents with given port, cred def and issuer seq")

        parser.add_argument('--port', required=False,
                            help='port where agent will listen')
        parser.add_argument('--credDefSeq', required=False,
                            help='cred def seq number')
        parser.add_argument('--issuerSeq', required=False,
                            help='issuer def seq number')

        args = parser.parse_args()
        return int(args.port), int(args.credDefSeq), int(args.issuerSeq)
    else:
        return None, None, None
