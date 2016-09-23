import ast
import datetime
import json
import os
from typing import Dict

from hashlib import sha256

from plenum.common.txn_util import createGenesisTxnFile
from sovrin.client.link_invitation import LinkInvitation
from sovrin.common.util import getConfig


from sovrin.anon_creds.constant import V_PRIME_PRIME, ISSUER, CRED_V, \
    ENCODED_ATTRS, CRED_E, CRED_A, NONCE, ATTRS, PROOF, REVEALED_ATTRS
from sovrin.anon_creds.cred_def import CredDef
from sovrin.anon_creds.issuer import InMemoryAttrRepo, Issuer
from sovrin.anon_creds.proof_builder import ProofBuilder
from sovrin.anon_creds.issuer import AttribDef, AttribType, Credential
from sovrin.anon_creds.cred_def import SerFmt

from plenum.cli.cli import Cli as PlenumCli
from prompt_toolkit.contrib.completers import WordCompleter
from prompt_toolkit.layout.lexers import SimpleLexer
from pygments.token import Token

from plenum.cli.helper import getClientGrams
from plenum.client.signer import Signer, SimpleSigner
from plenum.common.txn import DATA, RAW, ENC, HASH, NAME, VERSION, KEYS
from plenum.common.util import randomString, cleanSeed, getCryptonym

from sovrin.cli.helper import getNewClientGrams, Environment
from sovrin.client.client import Client
from sovrin.client.wallet import Wallet
from sovrin.common.txn import TARGET_NYM, STEWARD, ROLE, TXN_TYPE, NYM, \
    SPONSOR, TXN_ID, REFERENCE, USER, GET_NYM, ATTRIB, CRED_DEF, GET_CRED_DEF, \
    getTxnOrderedFields, ENDPOINT
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
client steward add bob (cli creates a signer and an ADDNYM for that signer's
cryptonym, and then an alias for bobto that cryptonym.)
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
        # Available environments
        self.envs = {
            "test": Environment("pool_transactions_sandbox",
                                "transactions_sandbox"),
            "live": Environment("pool_transactions_live",
                                "transactions_live")
        }
        # This specifies which environment the cli is connected to test or live
        self.activeEnv = None
        super().__init__(*args, **kwargs)

    @property
    def lexers(self):
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
            'add_attrs',
            'show_file',
            'conn'
            'load_file',
            'show_link',
            'sync_link'
        ]
        lexers = {n: SimpleLexer(Token.Keyword) for n in lexerNames}
        # Add more lexers to base class lexers
        return {**super().lexers, **lexers}

    @property
    def completers(self):
        completers = {}
        completers["nym"] = WordCompleter([])
        completers["role"] = WordCompleter(["USER", "SPONSOR", "STEWARD"])
        completers["send_nym"] = WordCompleter(["send", "NYM"])
        completers["send_get_nym"] = WordCompleter(["send", "GET_NYM"])
        completers["send_attrib"] = WordCompleter(["send", "ATTRIB"])
        completers["send_cred_def"] = WordCompleter(["send", "CRED_DEF"])
        completers["req_cred"] = WordCompleter(["request", "credential"])
        completers["gen_cred"] = WordCompleter(["generate", "credential"])
        completers["store_cred"] = WordCompleter(["store", "credential"])
        completers["list_cred"] = WordCompleter(["list", "CRED"])
        completers["gen_verif_nonce"] = WordCompleter(
            ["generate", "verification", "nonce"])
        completers["prep_proof"] = WordCompleter(
            ["prepare", "proof", "of"])
        completers["verif_proof"] = WordCompleter(
            ["verify", "status", "is"])
        completers["add_genesis"] = WordCompleter(
            ["add", "genesis", "transaction"])
        completers["init_attr_repo"] = WordCompleter(
            ["initialize", "mock", "attribute", "repo"])
        completers["add_attrs"] = WordCompleter(["add", "attribute"])
        completers["show_file"] = WordCompleter(["show"])
        completers["load_file"] = WordCompleter(["load"])
        completers["show_link"] = WordCompleter(["show", "link"])
        completers["conn"] = WordCompleter(["connect"])
        completers["env_name"] = WordCompleter(list(self.envs.keys()))
        completers["sync_link"] = WordCompleter(["sync"])
        return {**super().completers, **completers}

    def initializeGrammar(self):
        self.clientGrams = getClientGrams() + getNewClientGrams()
        super().initializeGrammar()

    @property
    def actions(self):
        actions = super().actions
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
                        self._addAttrsToProverAction,
                        self._storeCredAction,
                        self._genVerifNonceAction,
                        self._prepProofAction,
                        self._genCredAction,
                        self._showFile,
                        self._loadFile,
                        self._showLink,
                        self._connectTo,
                        self._syncLink
                        ])
        return actions

    def _buildWalletClass(self, nm):
        storage = WalletStorageFile.fromName(nm, self.basedirpath)
        return Wallet(nm, storage)

    @property
    def genesisTransactions(self):
        return self._genesisTransactions

    def reset(self):
        self._genesisTransactions = []

    def newNode(self, nodeName: str):
        config = getConfig()
        createGenesisTxnFile(self.genesisTransactions, self.basedirpath,
                             config.domainTransactionsFile,
                             getTxnOrderedFields(), reset=False)
        nodesAdded = super().newNode(nodeName)
        return nodesAdded

    def _printNotConnectedEnvMessage(self):
        self.print("Not connected to any environment. Please connect first.")
        self.print("Usage:")
        self.print("  connect ({})".format("|".join(sorted(self.envs.keys()))))

    def newClient(self, clientName, seed=None, identifier=None, signer=None,
                  wallet=None, config=None):
        if not self.activeEnv:
            self._printNotConnectedEnvMessage()
            return
        return super().newClient(clientName, seed=seed, identifier=identifier,
                                 signer=signer, wallet=wallet, config=config)

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

    def _getRole(self, matchedVars):
        role = matchedVars.get("role")
        validRoles = (USER, SPONSOR, STEWARD)
        if role and role not in validRoles:
            self.print("Invalid role. Valid roles are: {}".
                       format(", ".join(validRoles)), Token.Error)
            return False
        elif not role:
            role = USER
        return role

    def _getNym(self, nym):
        op = {
            TARGET_NYM: nym,
            TXN_TYPE: GET_NYM,
        }
        req, = self.activeClient.submit(op,
                                        identifier=self.activeSigner.identifier)
        self.print("Getting nym {}".format(nym))

        def getNymReply(reply, err):
            self.print("Transaction id for NYM {} is {}".
                       format(nym, reply[TXN_ID]), Token.BoldBlue)

        self.looper.loop.call_later(.2, self.ensureReqCompleted,
                                    req.reqId, self.activeClient, getNymReply)

    def _addNym(self, nym, role, other_client_name=None):
        op = {
            TARGET_NYM: nym,
            TXN_TYPE: NYM,
            ROLE: role
        }
        req, = self.activeClient.submit(op,
                                        identifier=self.activeSigner.identifier)
        printStr = "Adding nym {}".format(nym)

        if other_client_name:
            printStr = printStr + " for " + other_client_name
        self.print(printStr)

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
        if raw:
            op[RAW] = raw
            data = raw
        elif enc:
            op[ENC] = enc
            data = enc
        elif hsh:
            op[HASH] = hsh
            data = hsh

        req, = self.activeClient.submit(op,
                                        identifier=self.activeSigner.identifier)
        self.print("Adding attributes {} for {}".
                   format(data, nym), Token.BoldBlue)

        def out(reply, error):
            self.print("Attribute added for nym {}".format(reply[TARGET_NYM]),
                       Token.BoldBlue)

        self.looper.loop.call_later(.2, self.ensureReqCompleted,
                                    req.reqId, self.activeClient, out)

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
        return CredDef(attrNames=attributes, name=name,
                       version=version, ip=ip, port=port,
                       p_prime="prime1", q_prime="prime1")

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
        req, = self.activeClient.submit(op,
                                        identifier=self.activeSigner.identifier)
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

        def getEncodedAttrs(issuerId):
            attributes = self.activeClient.attributeRepo.getAttributes(issuerId)
            attribTypes = []
            for nm in attributes.keys():
                attribTypes.append(AttribType(nm, encode=True))
            attribsDef = AttribDef(self.name, attribTypes)
            attribs = attribsDef.attribs(**attributes).encoded()
            return {
                issuerId: next(iter(attribs.values()))
            }

        self.logger.debug("cred def is {}".format(credDef))
        keys = credDef[KEYS]
        pk = {
            issuerId: self.pKFromCredDef(keys)
        }
        masterSecret = self.activeClient.wallet.masterSecret

        proofBuilder = ProofBuilder(pk, masterSecret)
        proofBuilder.setParams(encodedAttrs=getEncodedAttrs(issuerId))

        if not masterSecret:
            self.activeClient.wallet.addMasterSecret(
                str(proofBuilder.masterSecret))

        #TODO: Should probably be persisting proof objects
        self.activeClient.proofBuilders[proofBuilder.id] = (proofBuilder,
                                                            credName,
                                                            credVersion,
                                                            issuerId)
        u = proofBuilder.U[issuerId]
        tokens = []
        tokens.append((Token.BoldBlue, "Credential request for {} for "
                                       "{} {} is: ".
                       format(proverId, credName, credVersion)))
        tokens.append((Token, "Credential id is "))
        tokens.append((Token.BoldBlue, "{} ".format(proofBuilder.id)))
        tokens.append((Token, "and U is "))
        tokens.append((Token.BoldBlue, "{}".format(u)))
        tokens.append((Token, "\n"))
        self.printTokens(tokens, separator='')

    @staticmethod
    def pKFromCredDef(keys):
        return CredDef.getPk(keys)

    def _initAttrRepoAction(self, matchedVars):
        if matchedVars.get('init_attr_repo') == 'initialize mock attribute repo':
            self.activeClient.attributeRepo = InMemoryAttrRepo()
            self.print("attribute repo initialized", Token.BoldBlue)
            return True

    def _genVerifNonceAction(self, matchedVars):
        if matchedVars.get('gen_verif_nonce') == 'generate verification nonce':
            # TODO: For now I am generating random interaction id, but we need
            # to come back to this
            interactionId = randomString(7)
            nonce = self.activeClient.generateNonce(interactionId)
            self.print("Verification nonce is {}".format(nonce), Token.BoldBlue)
            return True

    def _storeCredAction(self, matchedVars):
        if matchedVars.get('store_cred') == 'store credential':
            # TODO: Assuming single issuer credential only, make it accept
            # multi-issuer credential
            cred = matchedVars.get('cred')
            alias = matchedVars.get('alias').strip()
            proofId = matchedVars.get('prf_id').strip()
            credential = {}
            for val in cred.split(","):
                name, value = val.split('=', 1)
                name, value = name.strip(), value.strip()
                credential[name] = value

            proofBuilder, credName, credVersion, issuerId = \
                self.activeClient.proofBuilders[proofId]
            credential[ISSUER] = issuerId
            credential[NAME] = credName
            credential[VERSION] = credVersion
            # TODO: refactor to use issuerId
            credential[CRED_V] = str(next(iter(proofBuilder.vprime.values())) +
                                  int(credential[V_PRIME_PRIME]))
            credential[ENCODED_ATTRS] = {
                k: str(v) for k, v in
                next(iter(proofBuilder.encodedAttrs.values())).items()
            }
            # TODO: What if alias is not given (we don't have issuer id and
            # cred name here) ???
            # TODO: is the below way of storing  cred in dict ok?
            self.activeWallet.addCredential(alias, credential)
            self.print("Credential stored", Token.BoldBlue)
            return True

    @staticmethod
    def parseAttributeString(attrs):
        attrInput = {}
        for attr in attrs.split(','):
            name, value = attr.split('=')
            name, value = name.strip(), value.strip()
            attrInput[name] = value
        return attrInput

    def _addAttrsToRepoAction(self, matchedVars):
        if matchedVars.get('add_attrs') == 'add attribute':
            attrs = matchedVars.get('attrs')
            proverId = matchedVars.get('prover_id')
            attribTypes = []
            attributes = self.parseAttributeString(attrs)
            for name in attributes:
                attribTypes.append(AttribType(name, encode=True))
            attribsDef = AttribDef(self.name, attribTypes)
            attribs = attribsDef.attribs(**attributes)
            self.activeClient.attributeRepo.addAttributes(proverId, attribs)
            self.print("attribute added successfully for prover id {}".
                       format(proverId), Token.BoldBlue)
            return True

    def _addAttrsToProverAction(self, matchedVars):
        if matchedVars.get('add_attrs') == 'attribute known to':
            attrs = matchedVars.get('attrs')
            issuerId = matchedVars.get('issuer_id')
            attributes = self.parseAttributeString(attrs)
            # TODO: Refactor ASAP
            if not hasattr(self.activeClient, "attributes"):
                self.activeClient.attributeRepo = InMemoryAttrRepo()
            self.activeClient.attributeRepo.addAttributes(issuerId, attributes)
            self.print("attribute added successfully for issuer id {}".
                       format(issuerId), Token.BoldBlue)
            return True

    def _sendNymAction(self, matchedVars):
        if matchedVars.get('send_nym') == 'send NYM':
            nym = matchedVars.get('dest_id')
            role = self._getRole(matchedVars)
            self._addNym(nym, role)
            return True

    def _sendGetNymAction(self, matchedVars):
        if matchedVars.get('send_get_nym') == 'send GET_NYM':
            destId = matchedVars.get('dest_id')
            self._getNym(destId)
            return True

    def _sendAttribAction(self, matchedVars):
        if matchedVars.get('send_attrib') == 'send ATTRIB':
            nym = matchedVars.get('dest_id')
            raw = matchedVars.get('raw') \
                if matchedVars.get('raw') else None
            enc = ast.literal_eval(matchedVars.get('enc')) \
                if matchedVars.get('enc') else None
            hsh = matchedVars.get('hash') \
                if matchedVars.get('hash') else None
            self._addAttribToNym(nym, raw, enc, hsh)
            return True

    def _sendCredDefAction(self, matchedVars):
        if matchedVars.get('send_cred_def') == 'send CRED_DEF':
            credDef = self._buildCredDef(matchedVars)
            self.activeClient.wallet.addCredDefSk(credDef.name, credDef.version,
                                                  credDef.serializedSK)
            op = {TXN_TYPE: CRED_DEF, DATA: credDef.get(serFmt=SerFmt.base58)}
            req, = self.activeClient.submit(
                op, identifier=self.activeSigner.identifier)
            self.print("The following credential definition is published to the"
                       " Sovrin distributed ledger\n", Token.BoldBlue,
                       newline=False)
            self.print("{}".format(credDef.get(serFmt=SerFmt.base58)))
            self.looper.loop.call_later(.2, self.ensureReqCompleted,
                                        req.reqId, self.activeClient)
            return True

    # will get invoked when prover cli enters request credential command
    def _reqCredAction(self, matchedVars):
        if matchedVars.get('req_cred') == 'request credential':
            dest = matchedVars.get('issuer_id')
            credName = matchedVars.get('cred_name')
            proverName = matchedVars.get('prover_id')
            credVersion = matchedVars.get('version')
            self._getCredDefAndExecuteCallback(dest, credName, credVersion,
                                               self._sendCredReqToIssuer,
                                               credName,
                                               credVersion, dest, proverName)
            return True

    def _listCredAction(self, matchedVars):
        if matchedVars.get('list_cred') == 'list CRED':
            self.print('\n'.join(self.activeWallet.credNames))
            return True

    def _prepProofAction(self, matchedVars):
        if matchedVars.get('prep_proof') == 'prepare proof of':
            nonce = CredDef.getCryptoInteger(matchedVars.get('nonce'))
            revealedAttrs = (matchedVars.get('revealed_attrs'), )
            credAlias = matchedVars.get('cred_alias')

            credential = json.loads(self.activeClient.wallet.getCredential(credAlias))
            name = credential.get(NAME)
            version = credential.get(VERSION)
            issuer = credential.get(ISSUER)
            A = credential.get(CRED_A)
            e = credential.get(CRED_E)
            v = credential.get(CRED_V)
            cred = Credential(CredDef.getCryptoInteger(A), CredDef.getCryptoInteger(e),
                              CredDef.getCryptoInteger(v))
            credDef = self.activeClient.wallet.getCredDef(name, version, issuer)
            keys = credDef[KEYS]
            credDefPks = {
                issuer: self.pKFromCredDef(keys)
            }
            masterSecret = CredDef.getCryptoInteger(self.activeClient.wallet.
                                             masterSecret)
            attributes = self.activeClient.attributeRepo.getAttributes(issuer)
            attribTypes = []
            for nm in attributes.keys():
                attribTypes.append(AttribType(nm, encode=True))
            attribsDef = AttribDef(self.name, attribTypes)
            attribs = attribsDef.attribs(**attributes).encoded()
            encodedAttrs = {
                issuer: next(iter(attribs.values()))
            }
            proof = ProofBuilder.prepareProofAsDict(issuer=issuer,
                                                    credDefPks=credDefPks,
                                                    masterSecret=masterSecret,
                                                    creds={issuer: cred},
                                                    revealedAttrs=revealedAttrs,
                                                    nonce=nonce,
                                                    encodedAttrs=encodedAttrs)
            out = {}
            out[PROOF] = proof
            out[NAME] = name
            out[VERSION] = version
            out[ISSUER] = issuer
            out[NONCE] = str(nonce)
            out[ATTRS] = {
                issuer: {k: str(v) for k,v in next(iter(attribs.values())).items()}
            }
            out[REVEALED_ATTRS] = revealedAttrs
            self.print("Proof is: ", newline=False)
            self.print("{}".format(json.dumps(out)), Token.BoldBlue)
            return True

    def _verifyProofAction(self, matchedVars):
        if matchedVars.get('verif_proof') == 'verify status is':
            status = matchedVars.get('status')
            proof = json.loads(matchedVars.get('proof'))
            self._verifyProof(status, proof)
            return True

    def _verifyProof(self, status, proof):
        self._getCredDefAndExecuteCallback(proof["issuer"], proof[NAME],
                                           proof[VERSION], self.doVerification,
                                           status, proof)

    def doVerification(self, reply, err, status, proof):
        issuer = proof[ISSUER]
        credDef = self.activeClient.wallet.getCredDef(proof[NAME],
                                                      proof[VERSION], issuer)
        keys = credDef[KEYS]
        pk = {
            issuer: self.pKFromCredDef(keys)
        }
        prf = ProofBuilder.prepareProofFromDict(proof)
        attrs = {
            issuer: {k: CredDef.getCryptoInteger(v) for k, v in
                     next(iter(proof[ATTRS].values())).items()}
        }
        result = self.activeClient.verifyProof(pk, prf,
                                               CredDef.getCryptoInteger(
                                                   proof["nonce"]), attrs,
                                               proof[REVEALED_ATTRS])
        if not result:
            self.print("Proof verification failed", Token.BoldOrange)
        elif result and status in proof["revealedAttrs"]:
            self.print("Proof verified successfully", Token.BoldBlue)
        else:
            self.print("Status not in proof", Token.BoldOrange)

    def printUsage(self, msgs):
        self.print("\nUsage:")
        for m in msgs:
            self.print('  {}'.format(m))
        self.print("\n")

    def _loadInvitation(self, invitationData):
        # TODO: Lets not assume that the invitation file would contain these
        # keys. Let have a link file validation method
        linkInviation = invitationData["link-invitation"]
        linkInvitationName = linkInviation["name"]
        targetIdentifier = linkInviation["identifier"]
        targetEndPoint = linkInviation.get("endpoint", None)
        linkNonce = linkInviation["nonce"]
        claimRequests = invitationData.get("claim-requests", None)
        signature = invitationData["sig"]

        self.print("1 link invitation found for {}.".format(linkInvitationName))
        cseed = cleanSeed(None)
        alias = "cid-" + str(len(self.activeWallet.signers) + 1)
        signer = SimpleSigner(identifier=None, seed=cseed, alias=alias)
        self._addSignerToGivenWallet(signer, self.activeWallet)

        self.print("Creating Link for {}.".format(linkInvitationName))
        self.print("Generating Identifier and Signing key.")

        li = LinkInvitation(linkInvitationName,
                            signer.alias + ":" + signer.identifier, None,
                            linkInvitationName,
                            targetIdentifier, targetEndPoint, linkNonce,
                            claimRequests, signature)
        self.activeWallet.addLinkInvitation(li)

    def _loadFile(self, matchedVars):
        if matchedVars.get('load_file') == 'load':
            givenFilePath = matchedVars.get('file_path')
            filePath = SovrinCli._getFilePath(givenFilePath)
            if not filePath:
                self.print("Given file does not exist")
                msgs = ['show <file path>', 'load <file path>']
                self.printUsage(msgs)
                return True

            with open(filePath) as data_file:
                # TODO: What if it not JSON? Try Catch?
                invitationData = json.load(data_file)
            try:
                linkInvitation = invitationData["link-invitation"]
                # TODO: This check is not needed if while loading the file
                # its made sure that `linkInvitation` is JSON.
                if isinstance(linkInvitation, dict):
                    linkName = linkInvitation["name"]
                    existingLinkInvites = self.activeWallet.\
                        getMatchingLinkInvitations(linkName)
                    if len(existingLinkInvites) >= 1:
                        self.print("Link already exists")
                    else:
                        self._loadInvitation(invitationData)

                    self._printShowAndAcceptLinkUsage(linkName)
            except Exception as e:
                self.print('Error occurred during processing link '
                           'invitation: {}'.format(e))
            return True

    @staticmethod
    def _getFilePath(givenPath):
        curDirPath = os.path.dirname(os.path.abspath(__file__))
        sampleExplicitFilePath = curDirPath + "/../../" + givenPath
        sampleImplicitFilePath = curDirPath + "/../../sample/" + givenPath
        if os.path.exists(givenPath):
            return givenPath
        elif os.path.exists(sampleExplicitFilePath):
            return sampleExplicitFilePath
        elif os.path.exists(sampleImplicitFilePath):
            return sampleImplicitFilePath
        else:
            return None

    def _getInvitationMatchingLinks(self, linkName):
        exactMatched = {}
        likelyMatched = {}
        # if we want to search in all wallets, then,
        # change [self.activeWallet] to self.wallets.values()
        walletsToBeSearched = [self.activeWallet]  # self.wallets.values()
        for w in walletsToBeSearched:
            invitations = w.getMatchingLinkInvitations(linkName)
            for i in invitations:
                if i.name == linkName:
                    if w.name in exactMatched:
                        exactMatched[w.name].append(i)
                    else:
                        exactMatched[w.name] = [i]
                else:
                    if w.name in likelyMatched:
                        likelyMatched[w.name].append(i)
                    else:
                        likelyMatched[w.name] = [i]

        # Here is how the return dictionary should look like:
        # {
        #    "exactlyMatched": {
        #           "Default": [linkWithExactName],
        #           "WalletOne" : [linkWithExactName],
        #     }, "likelyMatched": {
        #           "Default": [similatMatches1, similarMatches2],
        #           "WalletOne": [similatMatches2, similarMatches3]
        #     }
        # }
        return {
            "exactlyMatched": exactMatched,
            "likelyMatched": likelyMatched
        }

    def _pingToEndpoint(self, endPoint):
        self.print("Ping to target endpoint: {} [Not Yet Implemented]".
                   format(endPoint))

    def _updateLinkWithLatestInfo(self, link, reply):
        data = json.loads(reply.get(DATA))
        endPoint = data.get('endpoint')
        if endPoint:
            link.updateEndPoint(endPoint)
            self.print('Endpoint received: {}'.format(endPoint))
            self._pingToEndpoint(endPoint)
        else:
            self.print('Endpoint not available')
        link.updateSyncInfo(datetime.datetime.now())
        self.activeWallet.addLinkInvitation(link)

    def _syncLinkPostEndPointRetrieval(self, reply, err, link: LinkInvitation):
        if err:
            self.print('Error occurred: {}'.format(err))
            return True

        self._updateLinkWithLatestInfo(link, reply)
        self._printShowAndAcceptLinkUsage(link.name)
        return True

    def _getTargetEndpoint(self, li):
        if self._isConnectedToAnyEnv():
            self.print("Synchronizing...")
            nym = getCryptonym(li.targetIdentifier)
            req = self.activeClient.doGetAttributeTxn(nym, ENDPOINT)[0]

            self.looper.loop.call_later(.2,
                                        self.ensureReqCompleted,
                                        req.reqId,
                                        self.activeClient,
                                        self._syncLinkPostEndPointRetrieval,
                                        li)
        else:
            if not self.activeEnv:
                self.print("Cannot sync because not connected. ")
                self._printNotConnectedEnvMessage()
            elif not self.activeClient.hasSufficientConnections:
                self.print("Cannot sync because not connected. "
                           "Please check if Sovrin is running")
            self._printConnectUsage()

    def _syncLinkInvitation(self, linkName):

        totalFound, exactlyMatchedLinks, likelyMatchedLinks = \
            self._getMatchingInvitationsDetail(linkName)

        if totalFound == 0:
            self._printNoLinkFoundMsg()
            return True

        if totalFound == 1:
            li = self._getOneLink(exactlyMatchedLinks, likelyMatchedLinks)
            if li.name != linkName:
                self.print('Expanding {} to "{}"'.format(linkName, li.name))

            if li.targetEndPoint:
                self._pingToEndpoint(li.targetEndPoint)
                self._printShowAndAcceptLinkUsage(li.name)
            else:
                self._getTargetEndpoint(li)
        else:
            self._printMoreThanOneLinkFoundMsg(linkName, exactlyMatchedLinks,
                                               likelyMatchedLinks)
        return True


    @staticmethod
    def cleanLinkName(name):
        return name.replace('"', '')

    def _printConnectUsage(self):
        msgs = ['connect (test | live)']
        self.printUsage(msgs)

    def _printSyncAndAcceptUsage(self, linkName):
        msgs = ['sync "{}"'.format(linkName),
                'accept invitation "{}"'.format(linkName)]
        self.printUsage(msgs)

    def _printShowAndAcceptLinkUsage(self, linkName):
        msgs = ['show link "{}"'.format(linkName),
                'accept invitation "{}"'.format(linkName)]
        self.printUsage(msgs)

    def _printShowAndLoadFileUsage(self):
        msgs = ['show <link file path>', 'load <link file path>']
        self.printUsage(msgs)

    def _printNoLinkFoundMsg(self):
        self.print("No matching link invitation(s) found in current keyring")
        self._printShowAndLoadFileUsage()

    def _isConnectedToAnyEnv(self):
        return self.activeEnv and self.activeClient.hasSufficientConnections

    def _syncLink(self, matchedVars):
        if matchedVars.get('sync_link') == 'sync':
            linkName = SovrinCli.cleanLinkName(matchedVars.get('link_name'))
            self._syncLinkInvitation(linkName)
            return True

    def _getMatchingInvitationsDetail(self, linkName):
        linkInvitations = self._getInvitationMatchingLinks(
            SovrinCli.cleanLinkName(linkName))

        exactlyMatchedLinks = linkInvitations["exactlyMatched"]
        likelyMatchedLinks = linkInvitations["likelyMatched"]

        totalFound = sum([len(v) for v in {**exactlyMatchedLinks,
                                           **likelyMatchedLinks}.values()])
        return totalFound, exactlyMatchedLinks, likelyMatchedLinks

    @staticmethod
    def _getOneLink(exactlyMatchedLinks, likelyMatchedLinks) -> LinkInvitation:
        li = None
        if len(exactlyMatchedLinks) == 1:
            li = list(exactlyMatchedLinks.values())[0][0]
        else:
            li = list(likelyMatchedLinks.values())[0][0]
        return li

    def _printMoreThanOneLinkFoundMsg(self, linkName, exactlyMatchedLinks,
                                      likelyMatchedLinks):
        self.print('More than one link matches "{}"'.format(linkName))
        exactlyMatchedLinks.update(likelyMatchedLinks)
        for k, v in exactlyMatchedLinks.items():
            for li in v:
                self.print("{}".format(li.name))
        self.print("\nRe enter the command with more specific "
                   "link invitation name")
        self._printShowAndLoadFileUsage()

    def _showLink(self, matchedVars):
        if matchedVars.get('show_link') == 'show link':
            linkName = matchedVars.get('link_name').replace('"','')

            totalFound, exactlyMatchedLinks, likelyMatchedLinks = \
                self._getMatchingInvitationsDetail(linkName)

            if totalFound == 0:
                self._printNoLinkFoundMsg()
                return True

            if totalFound == 1:
                li = self._getOneLink(exactlyMatchedLinks, likelyMatchedLinks)

                if li.name != linkName:
                    self.print('Expanding {} to "{}"'.format(linkName, li.name))
                self.print("{}".format(li.getLinkInfoStr()))
                self._printSyncAndAcceptUsage(li.name)
            else:
                self._printMoreThanOneLinkFoundMsg(linkName,
                                                   exactlyMatchedLinks,
                                                   likelyMatchedLinks)

            return True

    def _showFile(self, matchedVars):
        if matchedVars.get('show_file') == 'show':
            givenFilePath = matchedVars.get('file_path')
            filePath = SovrinCli._getFilePath(givenFilePath)
            if not filePath:
                self.print("Given file does not exist")
                msgs = ['show <file path>']
                self.printUsage(msgs)
            else:
                with open(filePath, 'r') as fin:
                    self.print(fin.read())
                msgs = ['load {}'.format(givenFilePath)]
                self.printUsage(msgs)
            return True

    def canConnectToEnv(self, envName: str):
        if envName == self.activeEnv:
            return "Already connected to {}".format(envName)
        if envName not in self.envs:
            return "Unknown environment {}".format(envName)
        if not os.path.isfile(os.path.join(self.basedirpath,
                                           self.envs[envName].poolLedger)):
            return "Do not have information to connect to {}".format(envName)

    def _connectTo(self, matchedVars):
        if matchedVars.get('conn') == 'connect':
            envName = matchedVars.get('env_name')
            envError = self.canConnectToEnv(envName)
            if envError:
                self.print(envError, token=Token.Error)
                self._printConnectUsage()
            else:
                # TODO: Just for the time being that we cannot accidentally
                # connect to live network even if we have a ledger for live
                # nodes.Once we have `live` exposed to the world,
                # this would be changed.
                if envName == "live":
                    self.print("Cannot connect to live environment. Contact"
                               " Sovrin.org to find out more!")
                    return True
                # Using `_activeClient` instead of `activeClient` since using
                # `_activeClient` will initialize a client if not done already
                if self._activeClient:
                    self.print("Disconnecting from {}".format(envName))
                    self._activeClient = None
                config = getConfig()
                config.poolTransactionsFile = self.envs[envName].poolLedger
                config.domainTransactionsFile = \
                    self.envs[envName].domainLedger
                self.activeEnv = envName
                self._buildClientIfNotExists(config)
                self.print("Connecting to {}".format(envName))
                # Prompt has to be changed, so it show the environment too
                self._setPrompt(self.currPromptText)
            return True

    def getStatus(self):
        # TODO: This needs to show active keyring and active identifier
        if not self.activeEnv:
            self._printNotConnectedEnvMessage()
        else:
            if self.activeClient.hasSufficientConnections:
                msg = "Connected to {} Sovrin network".format(self.activeEnv)
            else:
                msg = "Attempting connection to {} Sovrin network".\
                    format(self.activeEnv)
            self.print(msg)

    def _setPrompt(self, promptText):
        if self.activeEnv and \
                not promptText.endswith("@{}".format(self.activeClient)):
            promptText = "{}@{}".format(promptText, self.activeEnv)
        super()._setPrompt(promptText)

    # This function would be invoked, when, issuer cli enters the send GEN_CRED
    # command received from prover. This is required for demo for sure, we'll
    # see if it will be required for real execution or not
    def _genCredAction(self, matchedVars):
        if matchedVars.get('gen_cred') == 'generate credential':
            proverId = matchedVars.get('prover_id')
            credName = matchedVars.get('cred_name')
            credVersion = matchedVars.get('cred_version')
            uValue = matchedVars.get('u_value')
            credDef = self.activeClient.wallet.getCredDef(
                credName, credVersion, self.activeSigner.identifier)
            keys = credDef[KEYS]
            pk = self.pKFromCredDef(keys)
            attributes = self.activeClient.attributeRepo.\
                getAttributes(proverId).encoded()
            if attributes:
                attributes = list(attributes.values())[0]
            sk = self.activeClient.wallet.getCredDefSk(credName, credVersion)
            cred = Issuer.generateCredential(uValue, attributes, pk, sk)
            # TODO: For real scenario, do we need to send this credential back
            # or it will be out of band?
            self.print("Credential: ", newline=False)
            self.print("A={}, e={}, vprimeprime={}".format(*cred),
                       Token.BoldBlue)
            # TODO: For real scenario, do we need to send this
            # credential back or it will be out of band?
            return True

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
    def bootstrapClientKey(client, node, identifier=None):
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
        client.submit(op, identifier=self.activeSigner.identifier)

    def print(self, msg, token=None, newline=True):
        super().print(msg, token=token, newline=newline)

    def printHelp(self):
        self.print("""{}-CLI, a simple command-line interface for a {} sandbox.
        Commands:
            help - Shows this help message
            help <command> - Shows the help message of <command>
            new - creates one or more new nodes or clients
            keyshare - manually starts key sharing of a node
            status - Shows general status of the sandbox
            status <node_name>|<client_name> - Shows specific status
            list - Shows the list of commands you can run
            license - Show the license
            exit - exit the command-line interface ('quit' also works)
            prompt <principal name> - Changes the prompt to <principal name>
            principals (a person like Alice, an organization like Faber College, or an IoT-style thing)
            load <invitation filename> - Creates the link, generates Identifier and signing keys
            show <invitation filename> - Shows the info about the link invitation
            show link <name> - Shows link info in case of one matching link, otherwise shows all the matching link <names>
            connect <test> |<live> - Let's you connect to the respective environment
            sync <link name> - Synchronizes the link between the endpoints""".
                   format(self.properName, self.fullName))

    def createFunctionMappings(self):
        from collections import defaultdict

        def promptHelper():
            self.print("""Changes the prompt to provided principal name
                Usage: prompt <principal name>""")

        def principalsHelper():
            self.print("A person like Alice, an organization like Faber College, or an IoT-style thing")

        def loadHelper():
            self.print("""Creates the link, generates Identifier and signing keys
                Usage: load <invitation filename>""")

        def defaultHelper():
            self.printHelp()

        def showHelper():
            self.print("""Shows the info about the link invitation
                Usage: show <invitation filename>""")

        def showLinkHelper():
            self.print("""Shows link info in case of one matching link, otherwise
                shows all the matching links
                Usage: show link <name>""")

        def connectHelper():
            self.print("""Let's you connect to the respective environment
                Usage: connect <test>|<live>""")

        def syncHelper():
            self.print("""Synchronizes the link between the endpoints
                Usage: sync <link name>""")

        def defaultHelper():
            self.printHelp()

        mappings = {
            'show': showHelper,
            'prompt': promptHelper,
            'principals': principalsHelper,
            'load': loadHelper,
            'show link': showLinkHelper,
            'connect': connectHelper,
            'sync': syncHelper
        }

        return defaultdict(lambda: defaultHelper, **mappings)
