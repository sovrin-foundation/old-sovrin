import ast
import json
from typing import Dict

from charm.core.math.integer import integer
from hashlib import sha256

from anoncreds.protocol.attribute_repo import InMemoryAttributeRepo
from anoncreds.protocol.credential_definition import CredentialDefinition, \
    serialize, base58encode, base58decodedInt, base58decode
from anoncreds.protocol.proof import Proof
from anoncreds.protocol.types import AttribsDef, AttribType, SerFmt, \
    IssuerPublicKey, Credential
from anoncreds.protocol.utils import encodeAttrs

from plenum.cli.cli import Cli as PlenumCli
from prompt_toolkit.contrib.completers import WordCompleter
from prompt_toolkit.layout.lexers import SimpleLexer
from pygments.token import Token

from plenum.cli.helper import getClientGrams
from plenum.client.signer import Signer, SimpleSigner
from plenum.common.txn import DATA, RAW, ENC, HASH, NAME, VERSION, IP, PORT, KEYS
from plenum.common.util import randomString

from sovrin.cli.helper import getNewClientGrams
from sovrin.client.client import Client
from sovrin.client.wallet import Wallet
from sovrin.common.txn import TARGET_NYM, STEWARD, ROLE, TXN_TYPE, \
    NYM, SPONSOR, TXN_ID, REFERENCE, USER, GET_NYM, ATTRIB, CRED_DEF, GET_CRED_DEF
from sovrin.common.util import getCredDefTxnData
from sovrin.persistence.wallet_storage_file import WalletStorageFile
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
    _genesisTransactions = []

    def __init__(self, *args, **kwargs):
        self.aliases = {}         # type: Dict[str, Signer]
        self.sponsors = set()
        self.users = set()
        super().__init__(*args, **kwargs)
        # self.loadGenesisTxns()

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
            'prep_proof',
            'verif_proof',
            'add_genesis',
            'req_cred',
            'gen_cred',
            'store_cred',
            'gen_verif_nonce',
            'init_attr_repo',
            'add_attrs'
        ]
        sovrinLexers = {n: SimpleLexer(Token.Keyword) for n in lexerNames}
        # Add more lexers to base class lexers
        self.lexers = {**self.lexers, **sovrinLexers}
        super().initializeGrammarLexer()

    def initializeGrammarCompleter(self):
        self.nymWC = WordCompleter([])
        self.completers["nym"] = self.nymWC
        self.completers["role"] = WordCompleter(["USER", "SPONSOR", "STEWARD"])
        self.completers["send_nym"] = WordCompleter(["send", "NYM"])
        self.completers["send_get_nym"] = WordCompleter(["send", "GET_NYM"])
        self.completers["send_attrib"] = WordCompleter(["send", "ATTRIB"])
        self.completers["send_cred_def"] = WordCompleter(["send", "CRED_DEF"])
        self.completers["req_cred"] = WordCompleter(["request", "credential"])
        self.completers["gen_cred"] = WordCompleter(["generate", "credential"])
        self.completers["store_cred"] = WordCompleter(["store", "credential"])
        self.completers["list_cred"] = WordCompleter(["list", "CRED"])
        self.completers["gen_verif_nonce"] = WordCompleter(["generate", "verification", "nonce"])
        self.completers["prep_proof"] = WordCompleter(["prepare", "proof", "of"])
        self.completers["verif_proof"] = WordCompleter(["verify", "status", "is"])
        self.completers["add_genesis"] = WordCompleter(["add", "genesis", "transaction"])
        self.completers["init_attr_repo"] = WordCompleter(["initialize", "mock", "attribute", "repo"])
        self.completers["add_attrs"] = WordCompleter(["add", "attribute"])

        super().initializeGrammarCompleter()

    def getActionList(self):
        actions = super().getActionList()
        # Add more actions to base class for sovrin CLI
        actions.extend([self._sendNymAction,
                        self._sendGetNymAction,
                        self._sendAttribAction,
                        self._sendCredDefAction,
                        self._reqCredAction,
                        self._listCredAction,
                        self._verifyProofAction,
                        self._addGenesisAction,
                        self._initAttrRepoAction,
                        self._addAttrsToRepoAction,
                        self._storeCredAction,
                        self._genVerifNonceAction,
                        self._prepProofAction,
                        self._genCredAction
                        ])
        return actions

    def _buildWalletClass(self, nm):
        storage = WalletStorageFile.fromName(nm, self.basedirpath)
        return Wallet(nm, storage)

    # def loadGenesisTxns(self):
    #     # TODO: Load from conf dir when its ready
    #     from sovrin.cli.genesisTxns import GENESIS_TRANSACTIONS
    #     self._genesisTransactions = GENESIS_TRANSACTIONS

    @property
    def genesisTransactions(self):
        # if not self._genesisTransactions:
        #     self.loadGenesisTxns()
        return self._genesisTransactions

    def reset(self):
        self._genesisTransactions = []
        # self.loadGenesisTxns()

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

    def newClient(self, clientName, seed=None, identifier=None, signer=None,
                  wallet=None):
        return super().newClient(clientName, seed=seed, identifier=identifier,
                          signer=signer, wallet=wallet)
        # if clientName == "steward":
        #     for txn in self._genesisTransactions:
        #         if txn[TARGET_NYM] == identifier and txn[ROLE] == STEWARD:
        #             self.print("Steward activated", Token.BoldBlue)
        #             # Only one steward is supported for now
        #             return super().newClient(clientName,
        #                                      seed=STEWARD_SEED,
        #                                      signer=signer)
        #     else:
        #         self.print("No steward found with identifier {}".
        #                    format(identifier), Token.Error)
        # elif clientName in self.aliases:
        #     return super().newClient(clientName, signer=self.aliases[clientName])
        # else:
        #     self.print("{} must be first be added by a sponsor or steward".
        #                format(clientName), Token.Error)

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
        validRoles = (USER, SPONSOR, STEWARD)
        if role and role not in validRoles:
            self.print("Invalid role. Valid roles are: {}".format(", ".join(validRoles)), Token.Error)
            return False
        elif not role:
            role = USER
        return role

    def _getNym(self, nym):
        op = {
            TARGET_NYM: nym,
            TXN_TYPE: GET_NYM,
        }
        req, = self.activeClient.submit(op)
        self.print("Getting nym {}".format(nym), Token.BoldBlue)

        def getNymReply(reply, err):
            print("Reply fot from nym: {}", reply)

        self.looper.loop.call_later(.2, self.ensureReqCompleted,
                                    req.reqId, self.activeClient, getNymReply)

    def _addNym(self, nym, role, other_client_name=None):
        op = {
            TARGET_NYM: nym,
            TXN_TYPE: NYM,
            ROLE: role
        }
        req, = self.activeClient.submit(op)
        printStr = "Adding nym {}".format(nym)

        if other_client_name:
            printStr = printStr + " for " + other_client_name
        self.print(printStr, Token.BoldBlue)

        def out(reply, error):
            self.print("Nym {} added".format(reply[TARGET_NYM]), Token.BoldBlue)

        self.looper.loop.call_later(.2, self.ensureReqCompleted,
                                    req.reqId, self.activeClient, out)
        return True

    def _addAttribToNym(self, nym, raw, enc, hsh):
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

        req, = self.activeClient.submit(op)
        self.print("Adding attributes {} for {}".
                   format(data, nym), Token.BoldBlue)
        self.looper.loop.call_later(.2, self.ensureReqCompleted,
                                    req.reqId, self.activeClient)

    def _addCredDef(self, matchedVars):
        credDef = self._buildCredDef(matchedVars)
        self.activeClient.wallet.addCredDefSk(credDef.name, credDef.version,
                                              credDef.serializedSK)
        op = {TXN_TYPE: CRED_DEF, DATA: credDef.get(serFmt=SerFmt.base58)}
        req, = self.activeClient.submit(op, identifier=self.activeSigner.identifier)
        self.print("The following credential definition is published to the"
                   " Sovrin distributed ledger  \n{}".
                   format(credDef.get(serFmt=SerFmt.base58)), Token.BoldBlue)
        self.looper.loop.call_later(.2, self.ensureReqCompleted,
                                    req.reqId, self.activeClient)

    @staticmethod
    def _buildCredDef(matchedVars):
        """
        Helper function to build CredentialDefinition function from given values
        """
        name = matchedVars.get('name')
        version = matchedVars.get('version')
        ip = matchedVars.get('ip')
        port = matchedVars.get('port')
        keys = matchedVars.get('keys')
        attributes = [s.strip() for s in keys.split(",")]
        return CredentialDefinition(attrNames=attributes, name=name,
                                    version=version, ip=ip, port=port,
                                    # TODO: Just for testing, Remove once done
                                    p_prime=integer(157329491389375793912190594961134932804032426403110797476730107804356484516061051345332763141806005838436304922612495876180233509449197495032194146432047460167589034147716097417880503952139805241591622353828629383332869425029086898452227895418829799945650973848983901459733426212735979668835984691928193677469),
                                    q_prime=integer(151323892648373196579515752826519683836764873607632072057591837216698622729557534035138587276594156320800768525825023728398410073692081011811496168877166664537052088207068061172594879398773872352920912390983199416927388688319207946493810449203702100559271439586753256728900713990097168484829574000438573295723))

    # will get invoked when prover cli enters request credential command
    def _reqCred(self, matchedVars):
        dest = matchedVars.get('issuer_identifier')
        credName = matchedVars.get('name')
        credVersion = matchedVars.get('version')
        proverId = matchedVars.get('prover_id')

        self._getCredDefAndExecuteCallback(dest, credName, credVersion,
                                           self._sendCredReqToIssuer, credName,
                                           credVersion, dest, proverId)

    def _getCredDefAndExecuteCallback(self, dest, credName,
                                      credVersion, clbk, *args):
        op = {
            TARGET_NYM: dest,
            TXN_TYPE: GET_CRED_DEF,
            DATA: {
                NAME: credName,
                VERSION: credVersion
            }
        }
        req, = self.activeClient.submit(op)
        self.print("Getting cred def {} version {} for {}".
                   format(credName, credVersion, dest), Token.BoldBlue)

        self.looper.loop.call_later(.2, self.ensureReqCompleted,
                                    req.reqId, self.activeClient,
                                    clbk, *args)

    # callback function which once gets reply for GET_CRED_DEF will
    # send the proper command/msg to issuer
    def _sendCredReqToIssuer(self, reply, err, credName,
                                           credVersion, issuerId, proverId):
        credDef = self.activeClient.wallet.getCredDef(credName,
                                           credVersion, issuerId)
        self.logger.debug("cred def is {}".format(credDef))
        keys = credDef[KEYS]
        pk = {
            issuerId: self.pKFromCredDef(keys)
        }
        masterSecret = self.activeClient.wallet.getMasterSecret()
        if masterSecret:
            masterSecret = integer(int(masterSecret))
        proof = Proof(pk, masterSecret)
        attributes = self.activeClient.attributes[issuerId]
        attribTypes = []
        for nm in attributes.keys():
            attribTypes.append(AttribType(nm, encode=True))
        attribsDef = AttribsDef(self.name, attribTypes)
        attribs = attribsDef.attribs(**attributes).encoded()
        encodedAttrs = {
            issuerId: list(attribs.values())[0]
        }
        proof.setAttrs(encodedAttrs)
        if not masterSecret:
            self.activeClient.wallet.addMasterSecret(str(proof.masterSecret))

        #TODO: Should probably be persisting proof objects
        self.activeClient.proofs[proof.id] = (proof, credName, credVersion,
                                              issuerId)
        u = proof.U[issuerId]
        self.print("Credential request for {} for {} {} is: Proof id is {} "
                   "and U is {}".format(proverId, credName, credVersion,
                                        proof.id, u))

    @staticmethod
    def pKFromCredDef(keys):
        N = SovrinCli.strTointeger(base58decode(keys["N"]))
        S = SovrinCli.strTointeger(base58decode(keys["S"]))
        Z = SovrinCli.strTointeger(base58decode(keys["Z"]))
        R = {}
        for k, v in keys["R"].items():
            R[k] = SovrinCli.strTointeger(base58decode(v))
        return IssuerPublicKey(N, R, S, Z)

    # TODO: Move it to util module
    @staticmethod
    def strTointeger(n):
        if "mod" in n:
            a, b = n.split("mod")
            return integer(int(a.strip())) % integer(int(b.strip()))
        else:
            return integer(int(n))

    def _initAttrRepoAction(self, matchedVars):
        if matchedVars.get('init_attr_repo') == 'initialize mock attribute repo':
            self.activeClient.attributeRepo = InMemoryAttributeRepo()
            self.print("attribute repo initialized")
            return True

    def _genVerifNonceAction(self, matchedVars):
        if matchedVars.get('gen_verif_nonce') == 'generate verification nonce':
            # TODO: For now I am generating random interaction id, but we need
            # to come back to us,
            # assuming it will work, test cases will confirm it
            interactionId = randomString(7)
            nonce = self.activeClient.generateNonce(interactionId)
            self.print("Verification nonce is {}".format(nonce))
            return True

    def _storeCredAction(self, matchedVars):
        if matchedVars.get('store_cred') == 'store credential':
            # TODO: Assuming single issuer credential only, make it acccept multi-issuer credential
            # multi issuer credential
            cred = matchedVars.get('cred')
            alias = matchedVars.get('alias').strip()
            # credDef = matchedVars.get('cred_def')
            proofId = matchedVars.get('prf_id').strip()
            credential = {}
            for val in cred.split(","):
                name, value = val.split('=', 1)
                name, value = name.strip(), value.strip()
                credential[name] = value
            proof, credName, credVersion, issuerId = self.activeClient.proofs[proofId]
            credential["issuer"] = issuerId
            credential[NAME] = credName
            credential[VERSION] = credVersion
            # TODO: refactor to use issuerId
            credential["v"] = str(next(iter(proof.vprime.values())) + \
                              int(credential["vprimeprime"]))
            credential["encodedAttrs"] = {k: str(v) for k, v in next(iter(proof.attrs.values())).items()}
            # TODO: What if alias is not given (we don't have issuer id and cred name here) ???
            # TODO: is the below way of storing cred in dict ok?
            self.activeWallet.addCredential(alias, credential)
            self.print("Credential stored")
            return True

    def _addAttrsToRepoAction(self, matchedVars):
        if matchedVars.get('add_attrs') == 'add attribute':
            attrs = matchedVars.get('attrs')
            proverId = matchedVars.get('prover_id')

            attribTypes = []
            attrInput = {}
            for attr in attrs.split(','):
                name, value = attr.split('=')
                name, value = name.strip(), value.strip()
                attribTypes.append(AttribType(name, encode=True))
                attrInput[name] = [value]

            attribsDef = AttribsDef(self.name, attribTypes)
            attribs = attribsDef.attribs(**attrInput)
            self.activeClient.attributeRepo.addAttributes(proverId, attribs)
            self.print("attribute added successfully")
            return True

    def _sendNymAction(self, matchedVars):
        if matchedVars.get('send_nym') == 'send NYM':
            nym = matchedVars.get('dest_id')
            role = self._getRole(matchedVars)
            self._addNym(nym, role)
            # self.print("dest id is {}".format(nym))
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
            self._addAttribToNym(nym, raw, enc, hsh)
            return True

    def _sendCredDefAction(self, matchedVars):
        if matchedVars.get('send_cred_def') == 'send CRED_DEF':
            # name = matchedVars.get('name')
            # version = matchedVars.get('version')
            # type = matchedVars.get('type')
            # ip = matchedVars.get('ip')
            # port = matchedVars.get('port')
            # keys = matchedVars.get('keys')
            # self.print("passed values are {}, {}, {}, {}, {}, {}".
            #            format(name, version, type, ip, port, keys))
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
            self.print('\n'.join(self.activeWallet.credNames))
            return True

    def _prepProofAction(self, matchedVars):
        if matchedVars.get('prep_proof') == 'prepare proof of':
            nonce = integer(int(matchedVars.get('nonce')))
            revealedAttrs = (matchedVars.get('revealed_attrs'), )
            credAlias = matchedVars.get('cred_alias')
            credential = json.loads(self.activeClient.wallet.getCredential(credAlias))
            name = credential.get(NAME)
            version = credential.get(VERSION)
            issuer = credential.get("issuer")
            A = credential.get("A")
            e = credential.get("e")
            v = credential.get("v")
            cred = Credential(self.strTointeger(A), self.strTointeger(e),
                              self.strTointeger(v))
            # TODO: Need to create presentation token from crendential
            credDef = self.activeClient.wallet.getCredDef(name, version, issuer)
            keys = credDef[KEYS]
            pk = {
                issuer: self.pKFromCredDef(keys)
            }
            masterSecret = integer(int(self.activeClient.wallet.getMasterSecret()))
            # TODO: In walet for credential, store the corresponding credential
            # definition's name, version and issuerId so the corresponding
            # credential definition can be fetched and PK can be constructed
            # which is needed for the proof.
            # TODO: Have some way for Tyler to have attributes that are there
            # in issuer's repo. Maybe need a command
            # TODO: Build proof here and print it
            # attributes = self.activeClient.attributeRepo.getAttributes(
            #     self.activeSigner.alias).encoded()
            # if attributes:
            #     attributes = list(attributes.values())[0]
            attributes = self.activeClient.attributes[issuer]
            attribTypes = []
            for nm in attributes.keys():
                attribTypes.append(AttribType(nm, encode=True))
            attribsDef = AttribsDef(self.name, attribTypes)
            attribs = attribsDef.attribs(**attributes).encoded()
            encodedAttrs = {
                issuer: next(iter(attribs.values()))
            }
            prf = Proof.prepareProof(pk_i=pk, masterSecret=masterSecret,
                               credential={issuer: cred},
                               revealedAttrs=revealedAttrs, nonce=nonce,
                               attrs=encodedAttrs)
            self.print(
                "Proof is: {}".format((prf.c, prf.evect, prf.mvect,
                                            prf.vvect, prf.Aprime)))
            return True

    def _verifyProofAction(self, matchedVars):
        if matchedVars.get('verif_proof') == 'verify status is':
            status = matchedVars.get('status')
            proof = matchedVars.get('proof')

            # required to do verification: issuerId, name, version, proof, nonce, attrs, revealedAttrs
            # TODO: do verification here
            self.print("Proof verified successfully")
            return True

    # This function would be invoked, when, issuer cli enters the send GEN_CRED command received from prover
    # This is required for demo for sure, we'll see if it will be required for real execution or not
    def _genCredAction(self, matchedVars):
        if matchedVars.get('gen_cred') == 'generate credential':
            proverId = matchedVars.get('prover_id')
            credName = matchedVars.get('cred_name')
            credVersion = matchedVars.get('cred_version')
            uValue = integer(int(matchedVars.get('u_value')))
            credDef = self.activeClient.storage.getCredDef(
                self.activeClient.defaultIdentifier, credName, credVersion)
            keys = json.loads(credDef[KEYS])
            pk = self.pKFromCredDef(keys)
            attributes = self.activeClient.attributeRepo.getAttributes(proverId).encoded()
            if attributes:
                attributes = list(attributes.values())[0]
            sk = self.activeClient.wallet.getCredDefSk(credName, credVersion)
            sk = CredentialDefinition.getDeserializedSK(sk)
            p_prime, q_prime = CredentialDefinition.getPPrime(sk), \
                               CredentialDefinition.getQPrime(sk)
            cred = CredentialDefinition.generateCredential(uValue, attributes, pk,
                                                    p_prime, q_prime)

            self.print("Credential: A is {}, e is {}, vprime is {}".format(*cred))
            # TODO: For real scenario, do we need to send this credential back or it will be out of band?
            return True


    # def _genCred(self, reply, err, proverId, credName, credVersion, uValue):
    #     credName = reply.result[NAME]
    #     credVersion = reply.result[VERSION]
    #
    #     cred = self.activeClient.createCredential(proverId, credName, credVersion, uValue)
    #
    #     self.print("Credential is {}", format(cred))
    #     # TODO: For real scenario, do we need to send this credential back or it will be out of band?
    #     return True

    def _addGenesisAction(self, matchedVars):
        if matchedVars.get('add_genesis'):
            nym = matchedVars.get('dest_id')
            role = self._getRole(matchedVars)
            txn = {
                TXN_TYPE: NYM,
                TARGET_NYM: nym,
                TXN_ID: sha256(randomString(6).encode()).hexdigest(),
                ROLE: role.upper()
            }
            self.genesisTransactions.append(txn)
            self.print('Genesis transaction added.')
            return True

    @staticmethod
    def bootstrapClientKey(client, node):
        pass

    def ensureReqCompleted(self, reqId, client, clbk=None, *args):
        reply, err = client.replyIfConsensus(reqId)
        if reply is None:
            self.looper.loop.call_later(.2, self.ensureReqCompleted,
                                        reqId, client, clbk, *args)
        elif clbk:
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
