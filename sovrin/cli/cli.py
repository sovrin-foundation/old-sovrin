from plenum.cli.cli import Cli as PlenumCli
from pygments.token import Token

from sovrin.client.client import Client
from sovrin.server.node import Node


class SovrinCli(PlenumCli):
    name = 'sovrin'
    properName = 'Sovrin'
    fullName = 'Sovrin Identity platform'

    NodeClass = Node
    ClientClass = Client

    def newNode(self, nodeName: str):
        nodesAdded = super().newNode(nodeName)
        for node in nodesAdded:
            node.addGenesisTxns()