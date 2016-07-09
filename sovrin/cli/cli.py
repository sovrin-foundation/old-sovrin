import ast
from typing import Dict

from anoncreds.protocol.credential_definition import CredentialDefinition

from plenum.cli.cli import Cli as PlenumCli
from prompt_toolkit.contrib.completers import WordCompleter
from prompt_toolkit.layout.lexers import SimpleLexer
from pygments.token import Token

from plenum.cli.helper import getClientGrams
from plenum.client.signer import Signer, SimpleSigner
from plenum.common.txn import DATA, RAW, ENC, HASH, NAME, VERSION, IP, PORT, KEYS

from sovrin.cli.genesisTxns import STEWARD_SEED
from sovrin.cli.helper import getNewClientGrams
from sovrin.client.client import Client
from sovrin.common.txn import TARGET_NYM, STEWARD, ROLE, TXN_TYPE, \
    NYM, SPONSOR, TXN_ID, REFERENCE, USER, GET_NYM, ATTRIB, CRED_DEF, GET_CRED_DEF
from sovrin.common.util import getCredDefTxnData
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
        self.aliases = {}         # type: Dict[str, Signer]
        self.sponsors = set()
        self.users = set()
        super().__init__(*args, **kwargs)
        self.loadGenesisTxns()

    def initializeGrammar(self):
        self.clientGrams = getClientGrams() + getNewClientGrams()
        super().initializeGrammar()

    def initializeGrammarLexer(self):
        lexerNames = [
            'send_nym',
            'send_get_nym',
            'send_attrib',
            'send_cred_def',
            'send_cred',
            'list_cred',
            'send_proof',
            'add_genesis',
            'gen_cred'
        ]
        sovrinLexers = {n: SimpleLexer(Token.Keyword) for n in lexerNames}
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
        self.completers["req_cred"] = WordCompleter(["request", "credential"])
        self.completers["list_cred"] = WordCompleter(["list", "CRED"])
        self.completers["send_proof"] = WordCompleter(["send", "proof"])
        self.completers["gen_cred"] = WordCompleter(["send", "GEN_CRED"])
        self.completers["add_genesis"] = \
            WordCompleter(["add", "genesis", "transactions"])

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
                    self.print("Steward activated", Token.BoldBlue)
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
                client = self.clients[client_name]
                if client_name not in self.clients:
                    self.print("{} cannot add a new user".
                               format(client_name), Token.BoldOrange)
                    return True
                client_action = matchedVars.get('cli_action')
                if client_action == 'add':
                    other_client_name = matchedVars.get('other_client_name')
                    role = self._getRole(matchedVars)
                    signer = SimpleSigner()
                    nym = signer.verstr
                    return self._addNym(nym, role, other_client_name)

                elif matchedVars.get('send_attrib') == 'send ATTRIB':
                    nym = matchedVars.get('dest_id')
                    raw = matchedVars.get('raw')
                    enc = matchedVars.get('enc')
                    hsh = matchedVars.get('hash')
                    op = {
                        TXN_TYPE: ATTRIB,
                        TARGET_NYM: nym
                    }
                    data = None
                    if not raw:
                        op[RAW] = raw
                        data = raw
                    elif not enc:
                        op[ENC] = enc
                        data = enc
                    elif not hsh:
                        op[HASH] = hsh
                        data = hsh

                    req, = client.submit(op)
                    self.print("Adding attributes {} for {}".
                               format(data, nym), Token.BoldBlue)
                    self.looper.loop.call_later(.2, self.ensureReqCompleted,
                                            req.reqId, client)

    def _getRole(self, matchedVars):
        role = matchedVars.get("role")
        if role not in ("user", "sponsor"):
            self.print("Can only add a sponsor or user", Token.Error)
            return True
        else:
            role = USER if role == "user" else SPONSOR

        return role

    def _getNym(self, nym):
        op = {
            TARGET_NYM: nym,
            TXN_TYPE: GET_NYM,
        }
        req, = self.defaultClient.submit(op)
        self.print("Getting nym {}".format(nym), Token.BoldBlue)

        def getNymReply(reply, err):
            print("Reply fot from nym: {}", reply)

        self.looper.loop.call_later(.2, self.ensureReqCompleted,
                                    req.reqId, self.defaultClient, self.getNymReply)


    def _addNym(self, nym, role, other_client_name=None):
        op = {
            TARGET_NYM: nym,
            TXN_TYPE: NYM,
            ROLE: role
        }
        req, = self.defaultClient.submit(op)
        printStr = "Adding nym {}".format(nym)

        if other_client_name:
            printStr = printStr + " for " + other_client_name
        self.print(printStr, Token.BoldBlue)

        self.looper.loop.call_later(.2, self.ensureReqCompleted,
                                    req.reqId, self.defaultClient, self.addAlias,
                                    self.defaultClient, other_client_name,
                                    self.activeSigner)
        return True

    def _addAttrib(self, nym, raw, enc, hsh):
        op = {
            TXN_TYPE: ATTRIB,
            TARGET_NYM: nym
        }
        data = None
        if not raw:
            op[RAW] = raw
            data = raw
        elif not enc:
            op[ENC] = enc
            data = enc
        elif not hsh:
            op[HASH] = hsh
            data = hsh

        req, = self.defaultClient.submit(op)
        self.print("Adding attributes {} for {}".
                   format(data, nym), Token.BoldBlue)
        self.looper.loop.call_later(.2, self.ensureReqCompleted,
                                    req.reqId, self.defaultClient)

    def _addCredDef(self, matchedVars):
        credDef = self._buildCredDef(matchedVars)
        op = {TXN_TYPE: CRED_DEF, DATA: getCredDefTxnData(credDef)}
        req, = self.defaultClient.submit(op)
        self.print("Adding cred def {}".
                   format(credDef), Token.BoldBlue)
        self.looper.loop.call_later(.2, self.ensureReqCompleted,
                                    req.reqId, self.defaultClient)

    # will get invoked when prover cli enters request credential command
    def _reqCred(self, matchedVars):

        dest = matchedVars.get('issuer_identifier')
        cred_name = matchedVars.get('name')
        cred_version = matchedVars.get('version')

        self._getCredDefAndExecuteCallback(dest, self.defaultClient.defaultIdentifier,
                                           cred_name, cred_version,
                                           self._sendCredReqToIssuer)

    def _getCredDefAndExecuteCallback(self, dest, proverId, cred_name, cred_version, clbk, *args):
        op = {
            TARGET_NYM: dest,
            TXN_TYPE: GET_CRED_DEF,
            DATA: {
                NAME: cred_name,
                VERSION: cred_version
            }
        }
        req, = self.defaultClient.submit(op, identifier=dest)
        self.print("Getting cred def {} version {} for {}".
                   format(cred_name, cred_version, dest), Token.BoldBlue)

        self.looper.loop.call_later(.2, self.ensureReqCompleted,
                                    req.reqId, self.defaultClient,
                                    clbk, dest, proverId, *args)

    #  callback function which once gets reply for GET_CRED_DEF will send the proper command/msg to issuer
    def _sendCredReqToIssuer(self, reply, err, issuerId, proverId):
        credName = reply.result[NAME]
        credVersion = reply.result[VERSION]
        issuerIp = reply.result[IP]
        issuerPort = reply.result[PORT]
        keys = reply.result[KEYS]

        credDef = CredentialDefinition(attrNames=keys, name=credName, version=credVersion, ip=issuerIp, port=issuerPort)
        u = credDef.PK
        self.print("Credential request is: {}", format(u))
        # TODO: Handling sending of this command to real issuer (based on ip and port) is pending

    # helper function to build CredentialDefinition function from given values
    def _buildCredDef(self, matchedVars):
        name = matchedVars.get('name')
        version = matchedVars.get('version')
        # TODO: do we need to use type anywhere?
        # type = matchedVars.get('type')
        ip = matchedVars.get('ip')
        port = matchedVars.get('port')
        keys = ast.literal_eval(matchedVars.get('keys'))
        attributes = ast.literal_eval(keys.get('attributes'))

        return CredentialDefinition(attrNames=list(attributes.keys()), name=name,
                                    version=version, ip=ip, port=port)

    def _sendNymAction(self, matchedVars):
        if matchedVars.get('send_nym') == 'send NYM':
            nym = matchedVars.get('dest_id')
            role = self._getRole(matchedVars)
            self._addNym(nym, role)
            self.print("dest id is {}".format(nym))
            return True

    def _sendGetNymAction(self, matchedVars):
        if matchedVars.get('send_get_nym') == 'send GET_NYM':
            destId = matchedVars.get('dest_id')
            self._getNym(destId)
            self.print("dest id is {}".format(destId))
            return True

    def _sendAttribAction(self, matchedVars):
        if matchedVars.get('send_attrib') == 'send ATTRIB':
            nym = matchedVars.get('dest_id')
            raw = ast.literal_eval(matchedVars.get('raw'))
            enc = ast.literal_eval(matchedVars.get('enc'))
            hsh = matchedVars.get('hash')
            self.print("dest id is {}".format(nym))
            self.print("raw message is {}".format(raw))
            self._addAttrib(nym, raw, enc, hsh)
            return True

    def _sendCredDefAction(self, matchedVars):
        if matchedVars.get('send_cred_def') == 'send CRED_DEF':
            name = matchedVars.get('name')
            version = matchedVars.get('version')
            type = matchedVars.get('type')
            ip = matchedVars.get('ip')
            port = matchedVars.get('port')
            keys = ast.literal_eval(matchedVars.get('keys'))
            self.print("passed values are {}, {}, {}, {}, {}, {}".
                       format(name, version, type, ip, port, keys))
            self._addCredDef(matchedVars)
            return True

    def _reqCredAction(self, matchedVars):
        if matchedVars.get('req_cred') == 'request credential':
            dest = matchedVars.get('issuer_identifier')
            credName = matchedVars.get('cred_name')
            name = matchedVars.get('name')
            version = matchedVars.get('version')
            self.print("passed values are {}, {}, {}, {}".
                  format(dest, credName, name, version))
            self._reqCred(matchedVars)
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
            self.print("{}, {}, {}".format(attrName, credName, dest))
            return True

    # This is responsible to creating/generating credential on issuer side
    def _genCred(self, reply, err, issuerId, proverId, u, attr):
        credName = reply.result[NAME]
        credVersion = reply.result[VERSION]
        issuerIp = reply.result[IP]
        issuerPort = reply.result[PORT]
        keys = reply.result[KEYS]

        credDef = CredentialDefinition(attrNames=list(keys), name=credName, version=credVersion,
                                       ip=issuerIp, port=issuerPort)
        cred = credDef.generateCredential(u, attr)
        self.print("Here is credential for prover {}: \n {}", format(proverId, cred))
        # TODO: For real scenario, do we need to send this credential back or it will be out of band?

    # This function would be invoked, when, issuer cli enters the send GEN_CRED command received from prover
    # This is required for demo for sure, we'll see if it will be required for real execution or not
    def _genCredAction(self, matchedVars):
        if matchedVars.get('gen_cred') == 'send GEN_CRED':
            issuerId = matchedVars.get('issuer_id')
            proverId = matchedVars.get('prover_id')
            name = matchedVars.get('name')
            version = matchedVars.get('version')
            u = matchedVars.get('u')
            attr = matchedVars.get('attr')
            saveas = matchedVars.get('saveas')

            self._getCredDefAndExecuteCallback(issuerId, self.defaultClient.defaultIdentifier,
                                               name, version, self._genCred, u, attr)
    
    def _setGenesisAction(self, matchedVars):
        if matchedVars.get('add_genesis'):
            raise NotImplementedError

    def getActionList(self):
        actions = super().getActionList()
        # Add more actions to base class for sovrin CLI
        actions.extend([self._sendNymAction,
                        self._sendGetNymAction,
                        self._sendAttribAction,
                        self._sendCredDefAction,
                        self._reqCredAction,
                        self._listCredAction,
                        self._sendProofAction,
                        self._setGenesisAction])
        return actions

    @staticmethod
    def bootstrapClientKey(client, node):
        pass

    def ensureReqCompleted(self, reqId, client, clbk, *args):
        reply, err = client.replyIfConsensus(reqId)
        if reply is None:
            self.looper.loop.call_later(.2, self.ensureReqCompleted,
                                        reqId, client, clbk, *args)
        else:
            clbk(reply, err, *args)

    def addAlias(self, reply, err, client, alias, signer):
        txnId = reply[TXN_ID]
        op = {
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
