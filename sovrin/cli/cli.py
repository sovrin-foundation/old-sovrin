import ast
import datetime
import json
from typing import Dict, Any

import os
from hashlib import sha256
from plenum.common.signing import serializeForSig
from raet.nacling import Verifier as SigVerifier
from base64 import b64decode

from prompt_toolkit.contrib.completers import WordCompleter
from prompt_toolkit.layout.lexers import SimpleLexer
from pygments.token import Token

from plenum.cli.cli import Cli as PlenumCli
from plenum.cli.helper import getClientGrams
from plenum.client.signer import SimpleSigner
from plenum.common.txn import DATA, NAME, VERSION, KEYS, TYPE, \
    PORT, IP
from plenum.common.txn_util import createGenesisTxnFile
from plenum.common.util import randomString, cleanSeed, getCryptonym, isHex, \
    cryptonymToHex
from sovrin.agent.endpoint import Endpoint
from sovrin.anon_creds.constant import V_PRIME_PRIME, ISSUER, CRED_V, \
    ENCODED_ATTRS, CRED_E, CRED_A, NONCE, ATTRS, PROOF, REVEALED_ATTRS
from sovrin.anon_creds.cred_def import SerFmt
from sovrin.anon_creds.issuer import AttrRepo
from sovrin.anon_creds.issuer import AttribDef, AttribType, Credential
from sovrin.anon_creds.issuer import InMemoryAttrRepo, Issuer
from sovrin.anon_creds.proof_builder import ProofBuilder
from sovrin.anon_creds.verifier import Verifier
from sovrin.cli.helper import getNewClientGrams, Environment
from sovrin.client.client import Client
from sovrin.client.wallet.attribute import Attribute, LedgerStore
from sovrin.client.wallet.claim import Claim
from sovrin.client.wallet.cred_def import CredDefSk, CredDef, CredDefKey
from sovrin.client.wallet.credential import Credential as WalletCredential
from sovrin.client.wallet.wallet import Wallet
from sovrin.client.wallet.link_invitation import LinkInvitation, \
    TARGET_VER_KEY_SAME_AS_ID, LINK_STATUS_ACCEPTED, AvailableClaimData, \
    LINK_ITEM_PREFIX, ClaimRequest
from sovrin.common.identity import Identity
from sovrin.common.txn import TARGET_NYM, STEWARD, ROLE, TXN_TYPE, NYM, \
    SPONSOR, TXN_ID, REFERENCE, USER, getTxnOrderedFields, ENDPOINT
from sovrin.common.util import getConfig
from sovrin.server.node import Node
import sovrin.anon_creds.cred_def as CredDefModule


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
        self.attributeRepo = None   # type: AttrRepo
        self.proofBuilders = {}
        self.verifier = Verifier(randomString())
        _, port = self.nextAvailableClientAddr()
        self.endpoint = Endpoint(port, self.handleEndpointMsg)


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
            'sync_link',
            'show_claim',
            'accept_link_invite'
        ]
        lexers = {n: SimpleLexer(Token.Keyword) for n in lexerNames}
        # Add more lexers to base class lexers
        return {**super().lexers, **lexers}

    @property
    def completers(self):
        completers = {}
        completers["nym"] = WordCompleter([])
        completers["role"] = WordCompleter(["SPONSOR", "STEWARD"])
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
        completers["show_claim"] = WordCompleter(["show", "claim"])
        completers["accept_link_invite"] = WordCompleter(["accept",
                                                          "invitation"])

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
                        self._syncLink,
                        self._showClaim,
                        self._acceptInvitationLink
                        ])
        return actions

    @staticmethod
    def verifySig(identifier, signature, msg) -> bool:
        b64sig = signature.encode('utf-8')
        sig = b64decode(b64sig)
        vr = SigVerifier(identifier)
        return vr.verify(sig, msg)

    def _printShowAndReqClaimUsage(self, availableClaims):
        claimName = "|".join([cl.name for cl in availableClaims])
        msgs = ['show claim {}'.format(claimName),
                'request claim {}'.format(claimName)]
        self.printUsage(msgs)

    def _handleAcceptInviteResponse(self, msg: dict):
        signature = msg.get("signature")
        identifier = msg.get("identifier")
        del msg["signature"]
        ser = serializeForSig(msg)
        key = cryptonymToHex(identifier) if not isHex(identifier) else identifier
        isVerified = SovrinCli.verifySig(key, signature, ser)
        if isVerified:
            msg["signature"] = signature
            self.print("Signature accepted.")
            self.print("Trust established.")
            # Not sure how to know if the responder is a trust anchor or not
            self.print("Identifier created in Sovrin.")
            li = self._getLinkByTarget(getCryptonym(identifier))
            if li:
                availableClaims = []
                for cl in msg['claimsList']:
                    name, version, definition = cl['name'], cl['version'], \
                                                cl['definition']
                    availableClaims.append(AvailableClaimData(name, version))
                    self.activeWallet.addClaim(Claim(name, version, definition),
                                               li.targetIdentifier)
                li.updateAcceptanceStatus(LINK_STATUS_ACCEPTED)
                li.updateTargetVerKey(TARGET_VER_KEY_SAME_AS_ID)
                li.updateAvailableClaims(availableClaims)

                self.activeWallet.addLinkInvitation(li)

                if len(availableClaims) > 0:
                    self.print("Available claims: {}".
                               format(",".join([cl.name for cl in availableClaims])))
                    self._printShowAndReqClaimUsage(availableClaims)
            else:
                self.print("No matching invitation found")
        else:
            self.print("Signature rejected")

    def handleEndpointMsg(self, msg):
        if msg["type"] == "AVAIL_CLAIM_LIST":
            self._handleAcceptInviteResponse(msg)

    def sendToEndpoint(self, msg: Any, endpoint: str):
        pass


    def _buildWalletClass(self, nm):
        # DEPR
        # storage = WalletStorageFile.fromName(nm, self.basedirpath)
        return Wallet(nm)

    @property
    def genesisTransactions(self):
        return self._genesisTransactions

    def reset(self):
        self._genesisTransactions = []

    # @property
    # def activeWallet(self) -> Wallet:
    #     return super().activeWallet()

    def newNode(self, nodeName: str):
        config = getConfig()
        createGenesisTxnFile(self.genesisTransactions, self.basedirpath,
                             config.domainTransactionsFile,
                             getTxnOrderedFields(), reset=False)
        nodesAdded = super().newNode(nodeName)
        return nodesAdded

    def _printNotConnectedEnvMessage(self):
        self.print("Not connected to any environment. Please connect first.")
        self._printConnectUsage()

    def _printConnectUsage(self):
        msgs = ["connect ({})".format("|".join(sorted(self.envs.keys())))]
        self.printUsage(msgs)

    def newClient(self, clientName,
                  # seed=None,
                  # identifier=None,
                  # signer=None,
                  # wallet=None,
                  config=None):
        if not self.activeEnv:
            self._printNotConnectedEnvMessage()
            return

        # DEPR
        # return super().newClient(clientName, seed=seed, identifier=identifier,
        #                          signer=signer, wallet=wallet, config=config)
        client = super().newClient(clientName, config=config)
        if self.activeWallet:
            client.registerObserver(self.activeWallet.handleIncomingReply)
            pendingTxnsReqs = self.activeWallet.getPendingTxnRequests()
            for req in pendingTxnsReqs:
                self.activeWallet.pendRequest(req)
            reqs = self.activeWallet.preparePending()
            client.submitReqs(*reqs)
        return client

    @staticmethod
    def bootstrapClientKeys(idr, verkey, nodes):
        pass

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
        validRoles = (SPONSOR, STEWARD)
        if role and role not in validRoles:
            self.print("Invalid role. Valid roles are: {}".
                       format(", ".join(validRoles)), Token.Error)
            return False
        return role

    def _getNym(self, nym):
        identity = Identity(identifier=nym)
        req = self.activeWallet.requestIdentity(identity,
                                                sender=self.activeWallet.defaultId)
        self.activeClient.submitReqs(req)
        self.print("Getting nym {}".format(nym))

        def getNymReply(reply, err):
            self.print("Transaction id for NYM {} is {}".
                       format(nym, reply[TXN_ID]), Token.BoldBlue)

        self.looper.loop.call_later(.2, self.ensureReqCompleted,
                                    req.reqId, self.activeClient, getNymReply)

    def _addNym(self, nym, role, other_client_name=None):
        idy = Identity(nym, role=role)
        self.activeWallet.addSponsoredIdentity(idy)
        reqs = self.activeWallet.preparePending()
        req, = self.activeClient.submitReqs(*reqs)
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
        assert int(bool(raw)) + int(bool(enc)) + int(bool(hsh)) == 1
        if raw:
            l = LedgerStore.RAW
            data = raw
        elif enc:
            l = LedgerStore.ENC
            data = enc
        elif hsh:
            l = LedgerStore.HASH
            data = hsh
        else:
            raise RuntimeError('One of raw, enc, or hash are required.')

        attrib = Attribute(randomString(5), data, self.activeWallet.defaultId,
                           ledgerStore=LedgerStore.RAW)
        if nym != self.activeWallet.defaultId:
            attrib.dest = nym
        self.activeWallet.addAttribute(attrib)
        reqs = self.activeWallet.preparePending()
        req, = self.activeClient.submitReqs(*reqs)
        self.print("Adding attributes {} for {}".
                   format(data, nym), Token.BoldBlue)

        def chk(reply, error):
            assert self.activeWallet.getAttribute(attrib).seqNo is not None
            self.print("Attribute added for nym {}".format(reply[TARGET_NYM]),
                       Token.BoldBlue)

        self.looper.loop.call_later(.2, self.ensureReqCompleted,
                                    req.reqId, self.activeClient, chk)

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
        return CredDefModule.CredDef(attrNames=attributes, name=name,
                       version=version, ip=ip, port=port,
                       p_prime="prime1", q_prime="prime1")

    def _getCredDefAndExecuteCallback(self, dest, credName,
                                      credVersion, clbk, *args):
        credDefKey = CredDefKey(credName, credVersion, dest)
        req = self.activeWallet.requestCredDef(credDefKey,
                                               self.activeWallet.defaultId)
        # op = {
        #     TARGET_NYM: dest,
        #     TXN_TYPE: GET_CRED_DEF,
        #     DATA: {
        #         NAME: credName,
        #         VERSION: credVersion
        #     }
        # }
        # req, = self.activeClient.submit(op,
        #                                 identifier=self.activeSigner.identifier)
        self.activeClient.submitReqs(req)
        self.print("Getting cred def {} version {} for {}".
                   format(credName, credVersion, dest), Token.BoldBlue)

        self.looper.loop.call_later(.2, self.ensureReqCompleted,
                                    req.reqId, self.activeClient,
                                    clbk, *args)

    # callback function which once gets reply for GET_CRED_DEF will
    # send the proper command/msg to issuer
    def _sendCredReqToIssuer(self, reply, err, credName,
                                           credVersion, issuerId, proverId):
        credDef = self.activeWallet.getCredDef(CredDefKey(credName,
                                           credVersion, issuerId))

        def getEncodedAttrs(issuerId):
            attributes = self.attributeRepo.getAttributes(issuerId)
            attribTypes = []
            for nm in attributes.keys():
                attribTypes.append(AttribType(nm, encode=True))
            attribsDef = AttribDef(self.name, attribTypes)
            attribs = attribsDef.attribs(**attributes).encoded()
            return {
                issuerId: next(iter(attribs.values()))
            }

        self.logger.debug("cred def is {}".format(credDef))
        keys = credDef.keys
        pk = {
            issuerId: self.pKFromCredDef(keys)
        }
        masterSecret = self.activeWallet.masterSecret

        proofBuilder = ProofBuilder(pk, masterSecret)
        proofBuilder.setParams(encodedAttrs=getEncodedAttrs(issuerId))

        if not masterSecret:
            self.activeWallet.addMasterSecret(
                str(proofBuilder.masterSecret))

        #TODO: Should probably be persisting proof objects
        self.proofBuilders[proofBuilder.id] = (proofBuilder, credName,
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
        return CredDefModule.CredDef.getPk(keys)

    def _initAttrRepoAction(self, matchedVars):
        if matchedVars.get('init_attr_repo') == 'initialize mock attribute repo':
            self.attributeRepo = InMemoryAttrRepo()
            self.print("attribute repo initialized", Token.BoldBlue)
            return True

    def _genVerifNonceAction(self, matchedVars):
        if matchedVars.get('gen_verif_nonce') == 'generate verification nonce':
            # TODO: For now I am generating random interaction id, but we need
            # to come back to this
            interactionId = randomString(7)
            nonce = self.verifier.generateNonce(interactionId)
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
                self.proofBuilders[proofId]
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
            self.activeWallet.addCredential(WalletCredential(alias,
                                                             credential))
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
            self.attributeRepo.addAttributes(proverId, attribs)
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
                self.attributeRepo = InMemoryAttrRepo()
            self.attributeRepo.addAttributes(issuerId, attributes)
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
            sk = CredDefSk(credDef.name, credDef.version, credDef.serializedSK,
                           dest=self.activeWallet.defaultId)
            self.activeWallet.addCredDefSk(sk)
            data = credDef.get(serFmt=CredDefModule.SerFmt.base58)
            cd = CredDef(data[NAME], data[VERSION],
                                self.activeWallet.defaultId, data[TYPE],
                              data[IP], data[PORT], data[KEYS])
            self.activeWallet.addCredDef(cd)
            reqs = self.activeWallet.preparePending()

            # op = {TXN_TYPE: CRED_DEF, DATA: credDef.get(serFmt=SerFmt.base58)}
            # req, = self.activeClient.submit(
            #     op, identifier=self.activeSigner.identifier)
            self.activeClient.submitReqs(*reqs)
            self.print("The following credential definition is published to the"
                       " Sovrin distributed ledger\n", Token.BoldBlue,
                       newline=False)
            self.print("{}".format(credDef.get(serFmt=SerFmt.base58)))
            self.looper.loop.call_later(.2, self.ensureReqCompleted,
                                        reqs[0].reqId, self.activeClient)
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
            nonce = self.getCryptoInteger(matchedVars.get('nonce'))
            revealedAttrs = (matchedVars.get('revealed_attrs'), )
            credAlias = matchedVars.get('cred_alias')

            credential = self.activeWallet.getCredential(credAlias)
            data = credential.data
            name = data.get(NAME)
            version = data.get(VERSION)
            issuer = data.get(ISSUER)
            A = data.get(CRED_A)
            e = data.get(CRED_E)
            v = data.get(CRED_V)
            cred = Credential(self.getCryptoInteger(A),
                              self.getCryptoInteger(e),
                              self.getCryptoInteger(v))
            credDef = self.activeWallet.getCredDef(CredDefKey(name, version,
                                                              issuer))
            keys = credDef.keys
            credDefPks = {
                issuer: self.pKFromCredDef(keys)
            }
            masterSecret = self.getCryptoInteger(
                self.activeWallet.masterSecret)
            attributes = self.attributeRepo.getAttributes(issuer)
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

    @staticmethod
    def getCryptoInteger(x):
        return CredDefModule.CredDef.getCryptoInteger(x)

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
        credDef = self.activeWallet.getCredDef(CredDefKey(proof[NAME],
                                                      proof[VERSION], issuer))
        keys = credDef.keys
        pk = {
            issuer: self.pKFromCredDef(keys)
        }
        prf = ProofBuilder.prepareProofFromDict(proof)
        attrs = {
            issuer: {k: self.getCryptoInteger(v) for k, v in
                     next(iter(proof[ATTRS].values())).items()}
        }
        result = self.verifier.verifyProof(pk, prf,
                                               self.getCryptoInteger(
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
        claimRequestsJson = invitationData.get("claim-requests", None)
        claimRequests = []
        if claimRequestsJson:
            for cr in claimRequestsJson:
                claimRequests.append(
                    ClaimRequest(cr["name"], cr["version"]))

        signature = invitationData["sig"]

        self.print("1 link invitation found for {}.".format(linkInvitationName))
        cseed = cleanSeed(None)
        alias = "cid-" + str(len(self.activeWallet.identifiers) + 1)
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

    def _syncLinkPostEndPointRetrieval(self, reply, err, postSync,
                                       link: LinkInvitation):
        if err:
            self.print('Error occurred: {}'.format(err))
            return True

        self._updateLinkWithLatestInfo(link, reply)
        self.print("Link {} synced".format(link.name))
        postSync(link)
        return True

    def _printUsagePostSync(self, link):
        self._printShowAndAcceptLinkUsage(link.name)

    def _getTargetEndpoint(self, li, postSync):
        if self._isConnectedToAnyEnv():
            self.print("Synchronizing...")
            nym = getCryptonym(li.targetIdentifier)
            # req = self.activeClient.doGetAttributeTxn(nym, ENDPOINT)[0]
            attrib = Attribute(name=ENDPOINT,
                               value=None,
                               dest=nym,
                               ledgerStore=LedgerStore.RAW)
            # req = attrib.getRequest(self.activeWallet.defaultId)
            req = self.activeWallet.requestAttribute(
                attrib, sender=self.activeWallet.defaultId)
            self.activeClient.submitReqs(req)
            self.looper.loop.call_later(.2,
                                        self.ensureReqCompleted,
                                        req.reqId,
                                        self.activeClient,
                                        self._syncLinkPostEndPointRetrieval,
                                        postSync,
                                        li)
        else:

            if not self.activeEnv:
                self.print("Cannot sync because not connected.")
                self._printNotConnectedEnvMessage()
            elif not self.activeClient.hasSufficientConnections:
                self.print("Cannot sync because not connected. "
                           "Please check if Sovrin is running")
            self._printConnectUsage()

    def _getLinkByTarget(self, target) -> LinkInvitation:
        return self.activeWallet.getLinkInvitationByTarget(target)

    def _getOneLinkForFurtherProcessing(self, linkName):
        totalFound, exactlyMatchedLinks, likelyMatchedLinks = \
            self._getMatchingInvitationsDetail(linkName)

        if totalFound == 0:
            self._printNoLinkFoundMsg()
            return None

        if totalFound > 1:
            self._printMoreThanOneLinkFoundMsg(linkName, exactlyMatchedLinks,
                                               likelyMatchedLinks)
            return None
        li = self._getOneLink(exactlyMatchedLinks, likelyMatchedLinks)
        if li.name != linkName:
            self.print('Expanding {} to "{}"'.format(linkName, li.name))
        return li

    def _sendAcceptInviteToTargetEndpoint(self, link: LinkInvitation):
        self.print("Starting communication with {}".format(link.name))
        op = {
            "from": self.activeWallet.defaultId,
            "invitationNonce": link.nonce
        }
        signedNonce = self.activeWallet.signOp(op, self.activeWallet.defaultId)
        op["signedInvitationNonce"] = signedNonce
        self.sendToEndpoint(op, link.targetEndPoint)


    def _acceptLinkPostSync(self, link: LinkInvitation):
        self._sendAcceptInviteToTargetEndpoint(link)

    def _acceptLinkInvitation(self, linkName):
        li = self._getOneLinkForFurtherProcessing(linkName)
        if li:
            if li.isAccepted():
                self._printLinkAlreadyExcepted(li.name)
            else:
                self.print("Invitation not yet verified.")
                if not li.targetEndPoint:
                    self.print("Link not yet synchronized. "
                               "Attempting to sync...")
                    if self._isConnectedToAnyEnv():
                        self._getTargetEndpoint(li, self._acceptLinkPostSync)
                    else:
                        self.print("Invitation acceptance aborted.")
                        self.print("Cannot sync because not connected")
                        self._printNotConnectedEnvMessage()
                        return True
                else:
                    self._sendAcceptInviteToTargetEndpoint(li)


    def _syncLinkInvitation(self, linkName):
        li = self._getOneLinkForFurtherProcessing(linkName)
        if li:
            if li.targetEndPoint:
                self._pingToEndpoint(li.targetEndPoint)
                self._printShowAndAcceptLinkUsage(li.name)
            else:
                self._getTargetEndpoint(li, self._printUsagePostSync)


    @staticmethod
    def removeDoubleQuotes(name):
        return name.replace('"', '')

    # def _printConnectUsage(self):
    #     msgs = ['connect (test | live)']
    #     self.printUsage(msgs)

    def _printSyncAndAcceptUsage(self, linkName):
        msgs = ['sync "{}"'.format(linkName),
                'accept invitation "{}"'.format(linkName)]
        self.printUsage(msgs)

    def _printLinkAlreadyExcepted(self, linkName):
        self.print("Link {} is already accepted")

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

    def _acceptInvitationLink(self, matchedVars):
        if matchedVars.get('accept_link_invite') == 'accept invitation':
            linkName = SovrinCli.removeDoubleQuotes(matchedVars.get('link_name'))
            self._acceptLinkInvitation(linkName)
            return True

    def _syncLink(self, matchedVars):
        if matchedVars.get('sync_link') == 'sync':
            linkName = SovrinCli.removeDoubleQuotes(matchedVars.get('link_name'))
            self._syncLinkInvitation(linkName)
            return True

    def _getMatchingInvitationsDetail(self, linkName):
        linkInvitations = self._getInvitationMatchingLinks(
            SovrinCli.removeDoubleQuotes(linkName))

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
                if li.isAccepted():
                    self._printShowAndReqClaimUsage(li.availableClaims)
                else:
                    self._printSyncAndAcceptUsage(li.name)
            else:
                self._printMoreThanOneLinkFoundMsg(linkName,
                                                   exactlyMatchedLinks,
                                                   likelyMatchedLinks)

            return True

    def _printNoClaimFoundMsg(self):
        self.print("No matching claim(s) found in any links in current keyring")

    def _printMoreThanOneClaimFoundMsg(self, claimName, matchingLinks):
        self.print('More than one link matches "{}"'.format(claimName))
        for li in matchingLinks.items():
            self.print("{}".format(li.name))
        # TODO: Any suggestion in more than one link?

    def _getOneLinkAssociatedWithClaim(self, claimName) -> LinkInvitation:
        matchingLinks = self.activeWallet.getMatchingLinksByClaimName(claimName)

        if len(matchingLinks) == 0:
            self._printNoClaimFoundMsg()
            return None

        if len(matchingLinks) > 1:
            self._printMoreThanOneClaimFoundMsg(claimName, matchingLinks)
            return None

        return matchingLinks[0]

    def _showClaim(self, matchedVars):
        if matchedVars.get('show_claim') == 'show claim':
            claimName = SovrinCli.removeDoubleQuotes(
                matchedVars.get('claim_name'))
            matchingLink = self._getOneLinkAssociatedWithClaim(claimName)
            if matchingLink:
                self.print("Found claim {} in link {}".
                           format(claimName, matchingLink.name))
                cl = self.activeWallet.getClaimByNameAndProvider(
                    claimName, matchingLink.targetIdentifier)
                self.print(cl.getClaimInfoStr())
                msgs = ['request claim {}'.format(claimName)]
                self.printUsage(msgs)
            else:
                self.print("Claim not found in any link")
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
                self.ensureClientConnected()
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
            credDefKey = CredDefKey(credName, credVersion,
                                    self.activeWallet.defaultId)
            credDef = self.activeWallet.getCredDef(credDefKey)
            keys = credDef.keys
            pk = self.pKFromCredDef(keys)
            attributes = self.attributeRepo.\
                getAttributes(proverId).encoded()
            if attributes:
                attributes = list(attributes.values())[0]
            sk = self.activeWallet.getCredDefSk(credDefKey).secretKey
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

    def ensureClientConnected(self):
        if self._isConnectedToAnyEnv():
            self.print("Connected to {}".format(self.activeEnv))
        else:
            self.looper.loop.call_later(.2, self.ensureClientConnected)

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
