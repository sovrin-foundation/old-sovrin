from asyncio import BaseEventLoop
from typing import Iterable, Any, Union

from raet.road.stacking import RoadStack

from sovirin.agent.has_webserver import HasWebserver
from plenum.client.client import Client
from plenum.common.transaction_store import TransactionStore

# TODO Agent services
from sovirin.wallet import Wallet

"""
General benefit: insulates the Sponsor from the nuances of blockchain.
    Sponsor can interact with a simple RESTful service
    For example, the incrementing request id can be created and maintained by the Agent.
A blockchain monitoring service to notify the Sponsor of interesting transactions.
    For example, Susan changes her email address. The Church wants to
    know when that happens without watching every transaction on the
    blockchain.
Knows the nodes and broadcast transactions to all the nodes.
Authentication service. Sponsor can rely on Evernym to authenticate it's users.
Bundling of transactions for the Sponsor
Speeding up transactions (as a buffer so that the Sponsor can move faster than just interacting with the blockchain)

"""


class Agent(HasWebserver):

    def __init__(self, aid: str,
                 nodeReg: Iterable[Any]=None,  # an collection of anything that have host and port properties
                 stack: Union[RoadStack, dict]=None,
                 loop: BaseEventLoop=None
                 ):
        self.id = aid
        self.nodeReg = nodeReg
        self.loop = loop
        self.txnStore = TransactionStore()

        self.client = Client(clientId=aid,
                             nodeReg=nodeReg,
                             stack=stack)

        self.wallet = Wallet(self.client)
        self.sponsorWallets = {}

        HasWebserver.__init__(self, self.txnStore, self.loop)

    def createSponsorWallet(self, sponsorNym: str):
        self.sponsorWallets[sponsorNym] = Wallet(self.client)
