from plenum.cli.cli import Cli as PlenumCli

from sovrin.client.client import Client
from sovrin.server.node import Node


class SovrinCli(PlenumCli):
    name = 'sovrin'
    properName = 'Sovrin'
    fullName = 'Sovrin Identity platform'

    NodeClass = Node
    ClientClass = Client
