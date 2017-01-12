import argparse
import sys
import os

from plenum.common.signer_simple import SimpleSigner
from plenum.common.eventually import eventually
from plenum.test.test_stack import checkRemoteExists, CONNECTED

from sovrin.client.wallet.wallet import Wallet
from sovrin.common.config_util import getConfig
from sovrin.test.agent.bulldog_helper import bulldogLogger


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

        args = parser.parse_args()
        port = int(args.port) if args.port else None
        return port,
    else:
        return None,

    
def buildAgentWallet(name, seed):
    wallet = Wallet(name)
    wallet.addIdentifier(signer=SimpleSigner(seed=seed))
    return wallet


def buildFaberWallet():
    return buildAgentWallet("FaberCollege", b'Faber000000000000000000000000000')


def buildAcmeWallet():
    return buildAgentWallet("AcmeCorp", b'Acme0000000000000000000000000000')


def buildThriftWallet():
    return buildAgentWallet("ThriftBank", b'Thrift00000000000000000000000000')


def buildBulldogWallet():
    config = getConfig()
    baseDir = os.path.expanduser(config.baseDir)
    seedFileName = 'bulldog-seed'
    seedFilePath = '{}/{}'.format(baseDir, seedFileName)
    seed = 'Bulldog0000000000000000000000000'

    # if seed file is available, read seed from it
    if os.path.isfile(seedFilePath):
        try:
            with open(seedFilePath, mode='r+') as file:
                seed = file.read().strip(' \t\n\r')
        except OSError as e:
            bulldogLogger.warn('Error occurred while reading seed file:'
                               'error:{}'.format(e))
            raise e

    return buildAgentWallet('Bulldog', bytes(seed, encoding='utf-8'))
