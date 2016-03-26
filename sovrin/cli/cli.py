from plenum.cli.cli import Cli as PlenumCli
from prompt_toolkit.contrib.completers import WordCompleter
from pygments.token import Token

from sovrin.client.client import Client
from sovrin.common.txn import TARGET_NYM, STEWARD, ROLE
from sovrin.server.node import Node


"""
Objective
The plenum cli bootstraps client keys by just adding them to the nodes.
Sovrin needs the client nyms to be added as transactions first.
I'm thinking maybe the cli needs to support something like this:
new node all
<each node reports genesis transactions>
new client steward with identifier <nym> (nym matches the genesis transactions)
client steward add bob (cli creates a signer and an ADDNYM for that signer's cryptonym, and then an alias for bobto that cryptonym.)
new client bob (cli uses the signer previously stored for this client)
"""


class SovrinCli(PlenumCli):
    name = 'sovrin'
    properName = 'Sovrin'
    fullName = 'Sovrin Identity platform'

    NodeClass = Node
    ClientClass = Client
    _genesisTransactions = None

    def initializeGrammar(self):
        # self.grams = [
        #     "(\s* (?P<client_command>{}) \s+ (?P<node_or_cli>clients?)   \s+ (?P<client_name>[a-zA-Z0-9]+) \s*) |".format(self.relist(self.cliCmds))
        # ]
        # # The grammar should contain rules of `grams` first so that rules of
        # # `grams` take precedence over the base class' grammar rules
        # self.grams = grams + self.grams
        self.clientGrams = [
            "(\s* (?P<client_command>{}) \s+ (?P<node_or_cli>clients?)  \s+ (?P<client_name>[a-zA-Z0-9]+) \s*) \s+ (?P<with_identifier>with\s+identifier) \s+ (?P<nym>[a-zA-Z0-9]+) \s* |".format(self.relist(self.cliCmds)),

            "(\s* (?P<client>client) \s+ (?P<client_name>[a-zA-Z0-9]+) \s+ (?P<cli_action>send) \s+ (?P<msg>\{\s*.*\})  \s*)  |",
            "(\s* (?P<client>client) \s+ (?P<client_name>[a-zA-Z0-9]+) \s+ (?P<cli_action>show) \s+ (?P<req_id>[0-9]+)  \s*)  |",
            "(\s* (?P<add_key>add\s+key) \s+ (?P<verkey>[a-fA-F0-9]+) \s+ (?P<for_client>for\s+client) \s+ (?P<identifier>[a-zA-Z0-9]+) \s*)",
        ]
        super().initializeGrammar()

    def initializeGrammarCompleter(self):
        self.nymWC = WordCompleter([])
        self.completers["nym"] = self.nymWC
        super().initializeGrammarCompleter()

    def loadGenesisTxns(self):
        # TODO: Load from conf dir when its ready
        from sovrin.cli.genesisTxns import GENESIS_TRANSACTIONS
        self._genesisTransactions = GENESIS_TRANSACTIONS

    @property
    def genesisTransactions(self):
        if not self._genesisTransactions:
            self.loadGenesisTxns()
        return self._genesisTransactions

    def reset(self):
        self.loadGenesisTxns()

    def newNode(self, nodeName: str):
        nodesAdded = super().newNode(nodeName)
        genTxns = self.genesisTransactions
        for node in nodesAdded:
            tokens = [(Token.BoldBlue, "{} adding genesis transaction {}".
                       format(node.name, t)) for t in genTxns]
            self.printTokens(tokens=tokens, end='\n')
            node.addGenesisTxns(genTxns)
        return nodesAdded

    def newClient(self, clientName, seed=None, identifier=None):
        if clientName == "steward":
            for txn in self._genesisTransactions:
                if txn[TARGET_NYM] == identifier and txn[ROLE] == STEWARD:
                    super().newClient(clientName, identifier)
                    # Only one steward is supported for now
                    break
        else:
            pass

