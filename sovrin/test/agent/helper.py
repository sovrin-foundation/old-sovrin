import argparse

import sys

from plenum.common.signer_simple import SimpleSigner
from plenum.test.eventually import eventually
from plenum.test.helper import checkRemoteExists, CONNECTED
from sovrin.client.wallet.wallet import Wallet


def connectAgents(agent1, agent2):
    e1 = agent1.endpoint
    e2 = agent2.endpoint
    e1.connectTo(e2.ha)


def ensureAgentsConnected(looper, agent1, agent2):
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
        port = int(args.port) if args.port else None
        credDefSeq = int(args.credDefSeq) if args.credDefSeq else None
        issuerSeq = int(args.issuerSeq) if args.issuerSeq else None
        return port, credDefSeq, issuerSeq
    else:
        return None, None, None


def buildFaberWallet():
    name = "FaberCollege"
    wallet = Wallet(name)
    wallet.addSigner(signer=SimpleSigner(
        seed=b'Faber000000000000000000000000000'))
    return wallet


def buildAcmeWallet():
    name = "AcmeCorp"
    wallet = Wallet(name)
    wallet.addSigner(signer=SimpleSigner(
        seed=b'Acme0000000000000000000000000000'))
    return wallet


def buildThriftWallet():
    name = "ThriftBank"
    wallet = Wallet(name)
    wallet.addSigner(signer=SimpleSigner(
        seed=b'Thrift00000000000000000000000000'))
    return wallet
