import ast
from typing import Dict

import time

import asyncio

from plenum.cli.cli import Cli as PlenumCli
from prompt_toolkit.contrib.completers import WordCompleter
from prompt_toolkit.layout.lexers import SimpleLexer
from pygments.token import Token

from plenum.client.signer import Signer, SimpleSigner
from sovrin.cli.genesisTxns import STEWARD_SEED
from sovrin.client.client import Client
from sovrin.common.txn import TARGET_NYM, STEWARD, ROLE, ORIGIN, TXN_TYPE, \
    NYM, SPONSOR, TXN_ID, REFERENCE, USER
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

    def __init__(self, *args, **kwargs):
        outFilePath = kwargs.pop("outFilePath")
        self.outputFile = open(outFilePath, "w")
        super().__init__(*args, **kwargs)
        self.aliases = {}         # type: Dict[str, Signer]
        self.sponsors = set()
        self.users = set()
        self.loadGenesisTxns()

    def initializeGrammar(self):
        self.clientGrams = [
            # Regex for `new client steward with identifier <nym>`
            "(\s* (?P<client_command>{}) \s+ (?P<node_or_cli>clients?) \s+ (?P<client_name>[a-zA-Z0-9]+) \s*) \s+ (?P<with_identifier>with\s+identifier) \s+ (?P<nym>[a-zA-Z0-9=]+) \s* |".format(self.relist(self.cliCmds)),
            # Regex for `client steward add sponsor bob` or `client steward add user bob`
            "(\s* (?P<client>client) \s+ (?P<client_name>[a-zA-Z0-9]+) \s+ (?P<cli_action>add) \s+ (?P<role>sponsor|user) \s+ (?P<other_client_name>[a-zA-Z0-9]+) \s*)  |",
            # Regex for `new/status client bob`
            "(\s* (?P<client_command>{}) \s+ (?P<node_or_cli>clients?)   \s+ (?P<client_name>[a-zA-Z0-9]+) \s*) |".format(self.relist(self.cliCmds)),
            "(\s* (?P<client>client) \s+ (?P<client_name>[a-zA-Z0-9]+) \s+ (?P<cli_action>send) \s+ (?P<msg>\{\s*.*\})  \s*)  |",
            "(\s* (?P<client>client) \s+ (?P<client_name>[a-zA-Z0-9]+) \s+ (?P<cli_action>show) \s+ (?P<req_id>[0-9]+)  \s*)  |",
            "(\s* (?P<add_key>add\s+key) \s+ (?P<verkey>[a-fA-F0-9]+) \s+ (?P<for_client>for\s+client) \s+ (?P<identifier>[a-zA-Z0-9]+) \s*) |",
            "(\s* (?P<send_nym>send\s+NYM) \s+ (?P<dest>dest=)\s*(?P<dest_id>[a-fA-F0-9]+) \s*) |",
            "(\s* (?P<send_get_nym>send\s+GET_NYM) \s+ (?P<dest>dest=)\s*(?P<dest_id>[a-fA-F0-9]+) \s*) |",
            "(\s* (?P<send_attrib>send\s+ATTRIB) \s+ dest=\s*(?P<dest_id>[a-fA-F0-9]+) \s+ raw=(?P<raw>\{\s*.*\}) \s*) |",
            "(\s* (?P<send_cred_def>send\s+CRED_DEF) \s+ name=\"\s*(?P<name>[a-zA-Z0-9\s]+)\" \s+ version=\"(?P<version>[0-9\.]+)\" " \
                "\s+type=(?P<type>[a-zA-Z0-9]+) \s+ ip=(?P<ip>[0-9\.]+) \s+ port=(?P<port>[0-9]+) \s+ keys=(?P<keys>\{\s*.*\}) \s*) |",
            "(\s* (?P<send_cred>send\s+to) \s+ (?P<dest>[a-fA-F0-9]+) \s+ (?P<saveas>saveas)? \s+? (?P<cred_name>[a-zA-Z0-9\-_]+)? \s+? REQ_CRED \s+ " \
                " name=(?P<name>[a-zA-Z0-9\-]+) \s+ version=(?P<version>[0-9\.]+) \s+ attrs=(?P<attrs>[a-zA-Z0-9,]+) \s*) |",
            "(\s* (?P<list_cred>list\s+CRED) \s*) |",
            "(\s* (?P<send_proof>send\s+proof) \s+ of \s+ (?P<attr_name>[a-zA-Z0-9\-_]+) \s+ from \s+ (?P<cred_name>[a-zA-Z0-9\-_]+)? \s+ to \s+ " \
            " (?P<dest>[a-fA-F0-9]+) \s*) |",
            # TODO:KS Change base class to allow for extension, as of now we don't have any clean API for it
            "(\s* (?P<new_keypair>new_keypair) \s* (?P<alias>[a-zA-Z0-9]+)? \s*) |",
            "(\s* (?P<list_ids>list) \s+ (?P<ids>ids) \s*) |",
            "(\s* (?P<become>become) \s+ (?P<id>[a-zA-Z0-9]+) \s*) |",
            "(\s* (?P<use_keypair>use_keypair) \s+ (?P<keypair>[a-fA-F0-9]+) \s*)"
        ]
        super().initializeGrammar()

    def initializeGrammarLexer(self):
        sovrinLexers = {
            'send_nym': SimpleLexer(Token.Keyword),
            'send_get_nym': SimpleLexer(Token.Keyword),
            'send_attrib': SimpleLexer(Token.Keyword),
            'send_cred_def': SimpleLexer(Token.Keyword),
            'send_cred': SimpleLexer(Token.Keyword),
            'list_cred': SimpleLexer(Token.Keyword),
            'send_proof': SimpleLexer(Token.Keyword)
        }
        # Add more lexers to base class lexers
        self.lexers = {**self.lexers, **sovrinLexers}
        super().initializeGrammarLexer()

    def initializeGrammarCompleter(self):
        self.nymWC = WordCompleter([])
        self.completers["nym"] = self.nymWC
        self.completers["role"] = WordCompleter(["user", "sponsor"])
        self.completers["send_nym"] = WordCompleter(["send", "NYM"])
        self.completers["send_get_nym"] = WordCompleter(["send", "GET_NYM"])
        self.completers["send_attrib"] = WordCompleter(["send", "ATTRIB"])
        self.completers["send_cred_def"] = WordCompleter(["send", "CRED_DEF"])
        self.completers["send_cred"] = WordCompleter(["send", "to"])
        self.completers["list_cred"] = WordCompleter(["list", "CRED"])
        self.completers["send_proof"] = WordCompleter(["send", "proof"])
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
        if nodesAdded is not None:
            genTxns = self.genesisTransactions
            for node in nodesAdded:
                tokens = [(Token.BoldBlue, "{} adding genesis transaction {}".
                           format(node.name, t)) for t in genTxns]
                self.printTokens(tokens=tokens, end='\n')
                node.addGenesisTxns(genTxns)
        return nodesAdded

    def newClient(self, clientName, seed=None, identifier=None, signer=None):
        if clientName == "steward":
            for txn in self._genesisTransactions:
                if txn[TARGET_NYM] == identifier and txn[ROLE] == STEWARD:
                    self.print("Steward added", Token.BoldBlue)
                    # Only one steward is supported for now
                    if not signer:
                        signer = SimpleSigner(seed=STEWARD_SEED)
                    return super().newClient(clientName, signer=signer)
            else:
                self.print("No steward found with identifier {}".
                           format(identifier), Token.Error)
        elif clientName in self.aliases:
            return super().newClient(clientName, signer=self.aliases[clientName])
        else:
            self.print("{} must be first be added by a sponsor or steward".
                       format(clientName), Token.Error)

    def _clientCommand(self, matchedVars):
        if matchedVars.get('client') == 'client':
            r = super()._clientCommand(matchedVars)
            if not r:
                client_name = matchedVars.get('client_name')
                if client_name not in self.clients:
                    self.print("{} cannot add a new user".
                               format(client_name), Token.BoldOrange)
                    return True
                client_action = matchedVars.get('cli_action')
                if client_action == 'add':
                    other_client_name = matchedVars.get('other_client_name')
                    role = matchedVars.get("role")
                    if role not in ("user", "sponsor"):
                        self.print("Can only add a sponsor or user", Token.Error)
                        return True
                    else:
                        role = USER if role == "user" else SPONSOR
                    client = self.clients[client_name]
                    origin = client.getSigner().verstr
                    signer = SimpleSigner()
                    nym = signer.verstr
                    op = {
                        ORIGIN: origin,
                        TARGET_NYM: nym,
                        TXN_TYPE: NYM,
                        ROLE: role
                    }
                    req, = client.submit(op)
                    self.print("Adding nym {} for {}".
                               format(nym, other_client_name), Token.BoldBlue)
                    self.looper.loop.call_later(.2, self.ensureReqCompleted,
                                                req.reqId, client, self.addAlias,
                                                client, origin,
                                                other_client_name,
                                                signer)
                    return True

    def _sendNymAction(self, matchedVars):
        if matchedVars.get('send_nym') == 'send NYM':
            destId = matchedVars.get('dest_id')
            # TODO:LH Add code to send dest
            print("dest id is {}".format(destId))
            return True

    def _sendGetNymAction(self, matchedVars):
        if matchedVars.get('send_get_nym') == 'send GET_NYM':
            destId = matchedVars.get('dest_id')
            # TODO:LH Add code to send GET_NYM
            print("dest id is {}".format(destId))
            return True

    def _sendAttribAction(self, matchedVars):
        if matchedVars.get('send_attrib') == 'send ATTRIB':
            destId = matchedVars.get('dest_id')
            raw = ast.literal_eval(matchedVars.get('raw'))
            # TODO:LH Add code to send GET_NYM
            print("dest id is {}".format(destId))
            print("raw message is {}".format(raw))
            return True

    def _sendCredDefAction(self, matchedVars):
        if matchedVars.get('send_cred_def') == 'send CRED_DEF':
            name = matchedVars.get('name')
            version = matchedVars.get('version')
            type = matchedVars.get('type')
            ip = matchedVars.get('ip')
            port = matchedVars.get('port')
            keys = ast.literal_eval(matchedVars.get('keys'))
            # TODO:LH Add code to send GET_NYM
            print("passed values are {}, {}, {}, {}, {}, {}".format(name, version, type, ip, port, keys))
            return True

    def _sendCredAction(self, matchedVars):
        print(matchedVars)
        if matchedVars.get('send_cred') == 'send to':
            dest = matchedVars.get('dest')
            credName = matchedVars.get('cred_name')
            name = matchedVars.get('name')
            version = matchedVars.get('version')
            attrs = matchedVars.get('attrs')
            print("passed values are {}, {}, {}, {}, {}".format(dest, credName, name, version, attrs))
            return True

    def _listCredAction(self, matchedVars):
        if matchedVars.get('list_cred') == 'list CRED':
            # TODO:LH Add method to list creds
            return True

    def _sendProofAction(self, matchedVars):
        if matchedVars.get('send_proof') == 'send proof':
            attrName = matchedVars.get('attr_name')
            credName = matchedVars.get('cred_name')
            dest = matchedVars.get('dest')
            print("{}, {}, {}".format(attrName, credName, dest))
            return True

    def getActionList(self):
        actions = super().getActionList()
        # Add more actions to base class for sovrin CLI
        actions.extend([self._sendNymAction, self._sendGetNymAction,
                        self._sendAttribAction, self._sendCredDefAction,
                        self._sendCredAction, self._listCredAction,
                        self._sendProofAction])
        return actions

    @staticmethod
    def bootstrapClientKey(client, node):
        pass

    def ensureReqCompleted(self, reqId, client, clbk, *args):
        reply, err = client.replyIfConsensus(reqId)
        if reply is None:
            self.looper.loop.call_later(.2, reqId, client, clbk, *args)
        else:
            result = reply
            txnId = result[TXN_ID]
            clbk(txnId, *args)

    def addAlias(self, txnId, client, origin, alias, signer):
        op = {
            ORIGIN: origin,
            TARGET_NYM: alias,
            TXN_TYPE: NYM,
            # TODO: Should REFERENCE be symmetrically encrypted and the key
            # should then be disclosed in another transaction
            REFERENCE: txnId,
            ROLE: USER
        }
        self.print("Adding alias {}".format(alias), Token.BoldBlue)
        self.aliases[alias] = signer
        client.submit(op)

    def print(self, msg, token=None, newline=True):
        super().print(msg, token=token, newline=newline)
        if newline:
            msg += "\n"
        self.outputFile.write(msg)
        self.outputFile.flush()
        if msg == 'Goodbye.':
            self.outputFile.truncate(0)
