import ast
import datetime
import json
from typing import Dict, Any, Tuple, Callable
import uuid

import os
from hashlib import sha256

import collections

from plenum.client.signer import Signer

from ledger.util import F
from plenum.common.types import f

from prompt_toolkit.contrib.completers import WordCompleter
from prompt_toolkit.layout.lexers import SimpleLexer
from pygments.token import Token

from plenum.cli.cli import Cli as PlenumCli
from plenum.cli.helper import getClientGrams
from plenum.client.signer import SimpleSigner
from plenum.common.txn import DATA, NAME, VERSION, TYPE, ORIGIN, ATTRIBUTES
from plenum.common.txn_util import createGenesisTxnFile
from plenum.common.util import randomString, getCryptonym
from sovrin.agent.agent import WalletedAgent, EVENT_POST_ACCEPT_INVITE, \
    EVENT_NOTIFY_MSG
from sovrin.agent.msg_types import ACCEPT_INVITE, REQUEST_CLAIM, CLAIM_PROOF
from sovrin.anon_creds.constant import V_PRIME_PRIME, ISSUER, CRED_V, \
    ENCODED_ATTRS, CRED_E, CRED_A, NONCE, ATTRS, PROOF, REVEALED_ATTRS
from sovrin.anon_creds.issuer import AttrRepo
from sovrin.anon_creds.issuer import AttribDef, AttribType, Credential
from sovrin.anon_creds.issuer import InMemoryAttrRepo, Issuer
from sovrin.anon_creds.proof_builder import ProofBuilder
from sovrin.anon_creds.verifier import Verifier
from sovrin.cli.helper import getNewClientGrams, Environment, \
    USAGE_TEXT, NEXT_COMMANDS_TO_TRY_TEXT
from sovrin.client.client import Client
from sovrin.client.wallet.attribute import Attribute, LedgerStore
from sovrin.client.wallet.claim_def import IssuerPubKey, ClaimDef
from sovrin.client.wallet.credential import Credential as WalletCredential
from sovrin.client.wallet.wallet import Wallet
from sovrin.client.wallet.link import Link, constant
from sovrin.client.wallet.claim import ClaimProofRequest
from sovrin.common.exceptions import InvalidLinkException

from sovrin.common.identity import Identity
from sovrin.common.txn import TARGET_NYM, STEWARD, ROLE, TXN_TYPE, NYM, \
    SPONSOR, TXN_ID, REF, USER, getTxnOrderedFields, ENDPOINT
from sovrin.common.util import getConfig, getEncodedAttrs, ensureReqCompleted, \
    getCredDefIsrKeyAndExecuteCallback
from sovrin.server.node import Node
import sovrin.anon_creds.cred_def as CredDefModule

from anoncreds.protocol.cred_def_secret_key import CredDefSecretKey
from anoncreds.protocol.issuer_secret_key import IssuerSecretKey
from anoncreds.protocol.types import SerFmt
from anoncreds.protocol.utils import strToCharmInteger
from anoncreds.test.conftest import staticPrimes
from anoncreds.test.cred_def_test_store import MemoryCredDefStore
from anoncreds.test.issuer_key_test_store import MemoryIssuerKeyStore

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
        # DEPR JAL removed following because it doesn't seem right, testing now
        # LH: Shouldn't the Cli have a `Verifier` so it can act as a Verifier
        # entity too?
        # TODO: Confirm this decision
        self.verifier = Verifier(randomString(), MemoryCredDefStore(),
                                 MemoryIssuerKeyStore())
        _, port = self.nextAvailableClientAddr()
        self.curContext = (None, None, {})  # Current Link, Current Claim Req, set attributes
        self._agent = None

    @property
    def lexers(self):
        lexerNames = [
            'send_nym',
            'send_get_nym',
            'send_attrib',
            'send_cred_def',
            'send_isr_key',
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
            'show_claim_req',
            'req_claim',
            'accept_link_invite',
            'set_attr',
            'send_claim'
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
        completers["send_isr_key"] = WordCompleter(["send", "ISSUER_KEY"])
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
        completers["show_claim_req"] = WordCompleter(["show",
                                                      "claim", "request"])
        completers["req_claim"] = WordCompleter(["request", "claim"])
        completers["accept_link_invite"] = WordCompleter(["accept",
                                                          "invitation", "from"])

        completers["set_attr"] = WordCompleter(["set"])
        completers["send_claim"] = WordCompleter(["send", "claim"])
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
                        self._sendIssuerKeyAction,
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
                        self._reqClaim,
                        self._showClaimReq,
                        self._acceptInvitationLink,
                        self._setAttr,
                        self._sendClaim
                        ])
        return actions

    def _getSetAttrUsage(self):
        return ['set <attr-name> to <attr-value>']

    def _getSendClaimProofReqUsage(self, claimProofReqName=None, inviterName=None):
        return ['send claim {} to {}'.format(
            claimProofReqName or "<claim-req-name>",
            inviterName or "<inviter-name>")]

    def _getShowFileUsage(self, filePath=None):
        return ['show {}'.format(filePath or "<file-path>")]

    def _getLoadFileUsage(self, filePath=None):
        return ['load {}'.format(filePath or "<file-path>")]

    def _getShowClaimReqUsage(self, claimReqName=None):
        return ['show claim request "{}"'.format(
            claimReqName or '<claim-request-name>')]

    def _getShowClaimUsage(self, claimName=None):
        return ['show claim "{}"'.format(claimName or "<claim-name>")]

    def _getReqClaimUsage(self, claimName=None):
        return ['request claim "{}"'.format(claimName or "<claim-name>")]

    def _getShowLinkUsage(self, linkName=None):
        return ['show link "{}"'.format(linkName or "<link-name>")]

    def _getSyncLinkUsage(self, linkName=None):
        return ['sync "{}"'.format(linkName or "<link-name>")]

    def _getAcceptLinkUsage(self, linkName=None):
        return ['accept invitation from "{}"'.format(linkName or "<link-name>")]

    def _getPromptUsage(self):
        return ["prompt <principal name>"]

    @property
    def allEnvNames(self):
        return "|".join(sorted(self.envs.keys(),reverse=True))

    def _getConnectUsage(self):
        return ["connect <{}>".format(self.allEnvNames)]

    def _printPostShowClaimReqSuggestion(self, claimProofReqName, inviterName):
        msgs = self._getSetAttrUsage() + \
               self._getSendClaimProofReqUsage(claimProofReqName, inviterName)
        self.printSuggestion(msgs)

    def _printShowClaimReqUsage(self):
        self.printUsage(self._getShowClaimReqUsage())

    def _printMsg(self, notifier, msg):
        self.print(msg)


    def _printSuggestionPostAcceptLink(self, notifier,
                                       availableClaimNames,
                                       claimProofReqsCount):
        if len(availableClaimNames) > 0:
            claimName = "|".join([n for n in availableClaimNames])
            claimName = claimName or "<claim-name>"
            msgs = self._getShowClaimUsage(claimName) + \
                   self._getReqClaimUsage(claimName)
            self.printSuggestion(msgs)
        elif claimProofReqsCount > 0:
            self._printShowClaimReqUsage()
        else:
            self.print("")

    def sendToAgent(self, msg: Any, endpoint: Tuple):
        if not self.agent:
            return

        self.agent.connectTo(endpoint)

        # TODO: Refactor this
        def _send():
            self.agent.sendMessage(msg, destHa=endpoint)
            self.logger.debug("Message sent: {}".format(msg))

        if not self.agent.endpoint.isConnectedTo(ha=endpoint):
            self.ensureAgentConnected(endpoint, _send)
        else:
            _send()

    @property
    def walletClass(self):
        return Wallet

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

    def _printNotConnectedEnvMessage(self,
                                     prefix="Not connected to Sovrin network"):

        self.print("{}. Please connect first.".format(prefix))
        self._printConnectUsage()

    def _printConnectUsage(self):
        self.printUsage(self._getConnectUsage())

    def newClient(self, clientName,
                  config=None):
        if not self.activeEnv:
            self._printNotConnectedEnvMessage()
            # TODO: Return a dummy object that catches all attributes and
            # method calls and does nothing. Alo the dummy object should
            # initialise to null
            return DummyClient()

        client = super().newClient(clientName, config=config)
        if self.activeWallet:
            client.registerObserver(self.activeWallet.handleIncomingReply)
            self.activeWallet.pendSyncRequests()
            prepared = self.activeWallet.preparePending()
            client.submitReqs(*prepared)
        return client

    @property
    def agent(self):
        if not self.activeEnv:
            self._printNotConnectedEnvMessage()
            return None
        if self._agent is None:
            _, port = self.nextAvailableClientAddr()
            self._agent = WalletedAgent(name=randomString(6),
                                        basedirpath=self.basedirpath,
                                        client=self.activeClient,
                                        wallet=self.activeWallet,
                                        port=port)
            self._agent.registerEventListener(EVENT_NOTIFY_MSG, self._printMsg)
            self._agent.registerEventListener(EVENT_POST_ACCEPT_INVITE,
                                              self._printSuggestionPostAcceptLink)
            self.looper.add(self._agent)
        return self._agent

    @staticmethod
    def bootstrapClientKeys(idr, verkey, nodes):
        pass

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

        def getNymReply(reply, err, *args):
            self.print("Transaction id for NYM {} is {}".
                       format(nym, reply[TXN_ID]), Token.BoldBlue)

        self.looper.loop.call_later(.2, self._ensureReqCompleted,
                                    req.reqId, self.activeClient, getNymReply)

    def _addNym(self, nym, role, other_client_name=None):
        idy = Identity(nym, role=role)
        try:
            self.activeWallet.addSponsoredIdentity(idy)
        except Exception as e:
            if e.args[0] == 'identifier already added':
                pass
            else:
                raise e
        reqs = self.activeWallet.preparePending()
        req, = self.activeClient.submitReqs(*reqs)
        printStr = "Adding nym {}".format(nym)

        if other_client_name:
            printStr = printStr + " for " + other_client_name
        self.print(printStr)

        def out(reply, error, *args, **kwargs):
            self.print("Nym {} added".format(reply[TARGET_NYM]), Token.BoldBlue)

        self.looper.loop.call_later(.2, self._ensureReqCompleted,
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
        self.print("Adding attributes {} for {}".format(data, nym))

        def chk(reply, error, *args, **kwargs):
            assert self.activeWallet.getAttribute(attrib).seqNo is not None
            self.print("Attribute added for nym {}".format(reply[TARGET_NYM]),
                       Token.BoldBlue)

        self.looper.loop.call_later(.2, self._ensureReqCompleted,
                                    req.reqId, self.activeClient, chk)

    # @staticmethod
    def _buildCredDef(self, matchedVars):
        """
        Helper function to build CredentialDefinition function from given values
        """
        name = matchedVars.get('name')
        version = matchedVars.get('version')
        keys = matchedVars.get('keys')
        attrNames = [s.strip() for s in keys.split(",")]
        # TODO: Directly using anoncreds lib, should use plugin
        csk = CredDefSecretKey(*staticPrimes().get("prime1"))
        uid = self.activeWallet.addClaimDefSk(str(csk))
        claimDef = ClaimDef(seqNo=None,
                           attrNames=attrNames,
                           name=name,
                           version=version,
                           origin=self.activeWallet.defaultId,
                           typ=matchedVars.get(TYPE),
                           secretKey=uid)
        return claimDef

    def _buildIssuerKey(self, origin, reference):
        wallet = self.activeWallet
        claimDef = wallet.getClaimDef(seqNo=reference)
        if claimDef:
            csk = CredDefSecretKey.fromStr(wallet.getClaimDefSk(claimDef.secretKey))
            isk = IssuerSecretKey(claimDef, csk, uid=str(uuid.uuid4()))
            ipk = IssuerPubKey(N=isk.PK.N, R=isk.PK.R, S=isk.PK.S, Z=isk.PK.Z,
                               claimDefSeqNo=reference,
                               secretKeyUid=isk.uid, origin=wallet.defaultId)

            return ipk
        else:
            self.print("Reference {} not found".format(reference),
                       Token.BoldOrange)

    def _printCredReq(self, reply, err, credName,
                      credVersion, issuerId, proverId):
        # TODO: Should check for an existing proof builder if that exists for
        # the claim definition and issuer key
        proofBuilder = self.newProofBuilder(credName, credVersion, issuerId)
        u = proofBuilder.U[issuerId]
        self.setProofBuilderAttrs(proofBuilder, issuerId)
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

    def newProofBuilder(self, claimName, claimVersion, issuerId):
        # Assuming the claim def and issuer key come from the same entity
        claimDef = self.activeWallet.getClaimDef(
            (claimName, claimVersion, issuerId))
        issuerPubKey = self.activeWallet.getIssuerPublicKey(
            (issuerId, claimDef.seqNo))
        pk = {
            issuerId: issuerPubKey
        }
        masterSecret = self.activeWallet.masterSecret
        # if masterSecret:
        #     masterSecret = int(masterSecret)
        proofBuilder = ProofBuilder(pk, masterSecret)
        if not masterSecret:
            self.activeWallet.addMasterSecret(proofBuilder.masterSecret)
        # TODO: claimName, claimVersion and issuerId can be replaced with a
        # sequence number
        self.activeWallet.proofBuilders[proofBuilder.id] = (proofBuilder,
                                                            claimName,
                                                            claimVersion,
                                                            issuerId)
        return proofBuilder

    def setProofBuilderAttrs(self, pb, issuerId):
        attributes = self.attributeRepo.getAttributes(issuerId)
        pb.setParams(encodedAttrs=getEncodedAttrs(issuerId, attributes))

    @staticmethod
    def pKFromCredDef(keys):
        return CredDefModule.claimDef.getPk(keys)

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
                self.activeWallet.proofBuilders[proofId]
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
            if not self.canMakeSovrinRequest:
                return True
            nym = matchedVars.get('dest_id')
            role = self._getRole(matchedVars)
            self._addNym(nym, role)
            return True

    def _sendGetNymAction(self, matchedVars):
        if matchedVars.get('send_get_nym') == 'send GET_NYM':
            if not self.hasAnyKey:
                return True
            destId = matchedVars.get('dest_id')
            self._getNym(destId)
            return True

    def _sendAttribAction(self, matchedVars):
        if matchedVars.get('send_attrib') == 'send ATTRIB':
            if not self.canMakeSovrinRequest:
                return True
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
            if not self.canMakeSovrinRequest:
                return True
            claimDef = self._buildCredDef(matchedVars)
            self.activeWallet.addClaimDef(claimDef)
            reqs = self.activeWallet.preparePending()
            self.activeClient.submitReqs(*reqs)

            def published(reply, error, *args, **kwargs):
                self.print("The following credential definition is published"
                           "to the Sovrin distributed ledger\n", Token.BoldBlue,
                           newline=False)
                self.print("{}".format(claimDef.get(serFmt=SerFmt.base58)))
                self.print("Sequence number is {}".format(reply[F.seqNo.name]),
                           Token.BoldBlue)

            self.looper.loop.call_later(.2, self._ensureReqCompleted,
                                        reqs[0].reqId, self.activeClient,
                                        published)
            return True

    def _sendIssuerKeyAction(self, matchedVars):
        if matchedVars.get('send_isr_key') == 'send ISSUER_KEY':
            if not self.canMakeSovrinRequest:
                return True
            reference = int(matchedVars.get(REF))
            ipk = self._buildIssuerKey(self.activeWallet.defaultId,
                                             reference)
            if ipk:
                self.activeWallet.addIssuerPublicKey(ipk)
                reqs = self.activeWallet.preparePending()
                self.activeClient.submitReqs(*reqs)

                def published(reply, error, *args, **kwargs):
                    self.print("The following issuer key is published to the"
                               " Sovrin distributed ledger\n", Token.BoldBlue,
                               newline=False)
                    self.print("{}".format(ipk.get(serFmt=SerFmt.base58)))
                    self.print("Sequence number is {}".format(reply[F.seqNo.name]),
                               Token.BoldBlue)

                self.looper.loop.call_later(.2, self._ensureReqCompleted,
                                            reqs[0].reqId, self.activeClient,
                                            published)
            return True

    # will get invoked when prover cli enters request credential command
    def _reqCredAction(self, matchedVars):
        if matchedVars.get('req_cred') == 'request credential':
            if not self.canMakeSovrinRequest:
                return True
            origin = matchedVars.get('issuer_id')
            credName = matchedVars.get('cred_name')
            proverName = matchedVars.get('prover_id')
            credVersion = matchedVars.get('version')
            claimDefKey = (credName, credVersion, origin)
            getCredDefIsrKeyAndExecuteCallback(self.activeWallet,
                                                   self.activeClient,
                                                   self.print,
                                                   self.looper.loop,
                                               claimDefKey,
                                               self._printCredReq,
                                               pargs=(credName, credVersion,
                                                      origin, proverName))
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
            claimDef = self.activeWallet.getClaimDef((name, version, issuer))
            issuerPubKey = self.activeWallet.getIssuerPublicKey(
                (issuer, claimDef.seqNo))
            credDefPks = {
                issuer: issuerPubKey
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
        return strToCharmInteger(x) if isinstance(x, str) else x

    def _verifyProofAction(self, matchedVars):
        if matchedVars.get('verif_proof') == 'verify status is':
            status = matchedVars.get('status')
            proof = json.loads(matchedVars.get('proof'))
            self._verifyProof(status, proof)
            return True

    def _verifyProof(self, status, proof):
        claimDefKey = (proof[NAME], proof[VERSION], proof["issuer"])
        getCredDefIsrKeyAndExecuteCallback(self.activeWallet,
                                                   self.activeClient,
                                                   self.print,
                                                   self.looper.loop,
                                           claimDefKey,
                                                 self.doVerification,
                                                 pargs=(status, proof))

    def doVerification(self, reply, err, status, proof):
        issuer = proof[ISSUER]
        claimDef = self.activeWallet.getClaimDef((proof[NAME],
                                                      proof[VERSION], issuer))
        issuerPubKey = self.activeWallet.getIssuerPublicKey(
            (issuer, claimDef.seqNo))
        pk = {
            issuer: issuerPubKey
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

    def printUsageMsgs(self, msgs):
        for m in msgs:
            self.print('  {}'.format(m))
        self.print("\n")

    def printSuggestion(self, msgs):
        self.print("\n{}".format(NEXT_COMMANDS_TO_TRY_TEXT))
        self.printUsageMsgs(msgs)

    def printUsage(self, msgs):
        self.print("\n{}".format(USAGE_TEXT))
        self.printUsageMsgs(msgs)

    def _loadInvitation(self, invitationData):
        linkInvitation = invitationData["link-invitation"]
        remoteIdentifier = linkInvitation[f.IDENTIFIER.nm]
        signature = invitationData["sig"]
        linkInvitationName = linkInvitation[NAME]
        remoteEndPoint = linkInvitation.get("endpoint", None)
        linkNonce = linkInvitation[NONCE]
        claimProofRequestsJson = invitationData.get("claim-requests", None)

        claimProofRequests = []
        if claimProofRequestsJson:
            for cr in claimProofRequestsJson:
                claimProofRequests.append(
                    ClaimProofRequest(cr[NAME], cr[VERSION], cr[ATTRIBUTES]))

        self.print("1 link invitation found for {}.".format(linkInvitationName))
        # TODO: Assuming it is cryptographic identifier
        alias = "cid-" + str(len(self.activeWallet.identifiers) + 1)
        signer = SimpleSigner(alias=alias)
        self.activeWallet.addSigner(signer=signer)

        self.print("Creating Link for {}.".format(linkInvitationName))
        self.print("Generating Identifier and Signing key.")
        # TODO: Would we always have a trust anchor corresponding ot a link?
        trustAnchor = linkInvitationName
        li = Link(linkInvitationName,
                  signer.alias + ":" + signer.identifier,
                  trustAnchor, remoteIdentifier,
                  remoteEndPoint, linkNonce,
                  claimProofRequests, invitationData=invitationData)
        self.activeWallet.addLink(li)

    def _loadFile(self, matchedVars):
        if matchedVars.get('load_file') == 'load':
            givenFilePath = matchedVars.get('file_path')
            filePath = SovrinCli._getFilePath(givenFilePath)
            if not filePath:
                self.print("Given file does not exist")
                msgs = self._getShowFileUsage() + self._getLoadFileUsage()
                self.printUsage(msgs)
                return True

            with open(filePath) as data_file:
                try:
                    invitationData = json.load(
                        data_file, object_pairs_hook=collections.OrderedDict)
                    linkInvitation = invitationData.get("link-invitation")
                    if linkInvitation:
                        linkName = linkInvitation["name"]
                        existingLinkInvites = self.activeWallet.\
                            getMatchingLinks(linkName)
                        if len(existingLinkInvites) >= 1:
                            self.print("Link already exists")
                        else:
                            Link.validate(invitationData)
                            self._loadInvitation(invitationData)

                        self._printShowAndAcceptLinkUsage(linkName)
                    else:
                        self.print("No link invitation found in the given file")
                except ValueError:
                    self.print("Input is not a valid json"
                               "please check and try again")
                except InvalidLinkException as e:
                    self.print(e.args[0])

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
            invitations = w.getMatchingLinks(linkName)
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
        self.print("    Pinging target endpoint: {}".format(endPoint))
        self.print("        [Not Yet Implemented]")

    def _updateLinkWithLatestInfo(self, link: Link, reply):

        if DATA in reply and reply[DATA]:
            data = json.loads(reply[DATA])
            endPoint = data.get(ENDPOINT)
        else:
            endPoint = link.remoteEndPoint or constant.NOT_AVAILABLE

        link.remoteEndPoint = endPoint
        link.linkLastSynced = datetime.datetime.now()
        self.print("    Link {} synced".format(link.name))
        self.activeWallet.addLink(link)

        if endPoint != constant.NOT_AVAILABLE:
            self._pingToEndpoint(endPoint)

    def _syncLinkPostEndPointRetrieval(self, reply, err, postSync,
                                       link: Link, **kwargs):
        if err:
            self.print('Error occurred: {}'.format(err))
            return True

        self._updateLinkWithLatestInfo(link, reply)
        postSync(link)
        return True

    def _printUsagePostSync(self, link):
        self._printShowAndAcceptLinkUsage(link.name)

    def _getTargetEndpoint(self, li, postSync):
        if self._isConnectedToAnyEnv():
            self.print("    Synchronizing...")
            nym = getCryptonym(li.remoteIdentifier)
            attrib = Attribute(name=ENDPOINT,
                               value=None,
                               dest=nym,
                               ledgerStore=LedgerStore.RAW)
            req = self.activeWallet.requestAttribute(
                attrib, sender=self.activeWallet.defaultId)
            self.activeClient.submitReqs(req)
            self.looper.loop.call_later(.2,
                                        self._ensureReqCompleted,
                                        req.reqId,
                                        self.activeClient,
                                        self._syncLinkPostEndPointRetrieval,
                                        (postSync, li))
        else:
            if not self.activeEnv:
                self._printNotConnectedEnvMessage(
                    "Cannot sync because not connected")
            elif not self.activeClient.hasSufficientConnections:
                self.print("Cannot sync because not connected. "
                           "Please confirm if Sovrin network is running.")

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
        if SovrinCli.isNotMatching(linkName, li.name):
            self.print('Expanding {} to "{}"'.format(linkName, li.name))
        return li

    def _sendReqToTargetEndpoint(self, op, link: Link):
        op[f.IDENTIFIER.nm] = link.verkey
        op[NONCE] = link.nonce
        signature = self.activeWallet.signMsg(op, link.verkey)
        op[f.SIG.nm] = signature
        ip, port = link.remoteEndPoint.split(":")
        self.sendToAgent(op, (ip, int(port)))

    def sendReqClaim(self, reply, error, link, claimDefKey):
        name, version, origin = claimDefKey
        claimDef = self.activeWallet.getClaimDef(claimDefKey)
        if not claimDef.seqNo:
            self.looper.loop.call_later(.2, self.sendReqClaim,
                                        reply, error, link, claimDefKey)
        else:
            issuerPubKey = self.activeWallet.getIssuerPublicKey(
                (origin, claimDef.seqNo))
            if not issuerPubKey.seqNo:
                self.looper.loop.call_later(.2, self.sendReqClaim,
                                            reply, error, link, claimDefKey)
            else:
                self.logger.debug("Found both claimDef and issuerKey in wallet")
        # TODO: Should check for an existing proof builder if that exists for
        # the claim definition and issuer key
        proofBuilder = self.newProofBuilder(name, version, origin)
        uValue = proofBuilder.U[origin]
        op = {
            NONCE: link.nonce,
            TYPE: REQUEST_CLAIM,
            NAME: name,
            VERSION: version,
            ORIGIN: origin,
            'U': str(uValue)
        }
        signature = self.activeWallet.signMsg(op, link.verkey)
        op[f.SIG.nm] = signature
        self.print("Requesting claim {} from {}...".format(
            name, link.name))
        self._sendReqToTargetEndpoint(op, link)

    def _sendAcceptInviteToTargetEndpoint(self, link: Link):
        op = {
            TYPE: ACCEPT_INVITE
        }
        self._sendReqToTargetEndpoint(op, link)

    def _acceptLinkPostSync(self, link: Link):
        if link.isRemoteEndpointAvailable:
            self._sendAcceptInviteToTargetEndpoint(link)
        else:
            self.print("Remote endpoint not found, "
                       "can not connect to {}".format(link.name))

    def _acceptLinkInvitation(self, linkName):
        li = self._getOneLinkForFurtherProcessing(linkName)

        if li:
            if li.isAccepted:
                self._printLinkAlreadyExcepted(li.name)
            else:
                self.print("Invitation not yet verified.")
                if not li.linkLastSynced:
                    self.print("Link not yet synchronized.")

                if self._isConnectedToAnyEnv():
                    self.print("Attempting to sync...")
                    self._getTargetEndpoint(li, self._acceptLinkPostSync)
                else:
                    if li.isRemoteEndpointAvailable:
                        self._sendAcceptInviteToTargetEndpoint(li)
                    else:
                        self.print("Invitation acceptance aborted.")
                        self._printNotConnectedEnvMessage(
                            "Cannot sync because not connected")

    def _syncLinkInvitation(self, linkName):
        li = self._getOneLinkForFurtherProcessing(linkName)
        if li:
            self._getTargetEndpoint(li, self._printUsagePostSync)

    @staticmethod
    def isNotMatching(source, target):
        return source.lower() != target.lower()

    @staticmethod
    def removeDoubleQuotes(name):
        return name.replace('"', '')

    def _printSyncAndAcceptUsage(self, linkName):
        msgs = self._getSyncLinkUsage(linkName) + \
               self._getAcceptLinkUsage(linkName)
        self.printSuggestion(msgs)

    def _printLinkAlreadyExcepted(self, linkName):
        self.print("Link {} is already accepted\n".format(linkName))

    def _printShowAndAcceptLinkUsage(self, linkName=None):
        msgs = self._getShowLinkUsage(linkName) + \
               self._getAcceptLinkUsage(linkName)
        self.printSuggestion(msgs)

    def _printShowAndLoadFileUsage(self):
        msgs = self._getShowFileUsage() + self._getLoadFileUsage()
        self.printUsage(msgs)

    def _printShowAndLoadFileSuggestion(self):
        msgs = self._getShowFileUsage() + self._getLoadFileUsage()
        self.printSuggestion(msgs)

    def _printNoLinkFoundMsg(self):
        self.print("No matching link invitation(s) found in current keyring")
        self._printShowAndLoadFileSuggestion()

    def _isConnectedToAnyEnv(self):
        return self.activeEnv and self.activeClient.hasSufficientConnections

    def _acceptInvitationLink(self, matchedVars):
        if matchedVars.get('accept_link_invite') == 'accept invitation from':
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
    def _getOneLink(exactlyMatchedLinks, likelyMatchedLinks) -> Link:
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
        self._printShowAndAcceptLinkUsage()

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

                if SovrinCli.isNotMatching(linkName, li.name):
                    self.print('Expanding {} to "{}"'.format(linkName, li.name))

                self.print("{}".format(str(li)))
                if li.isAccepted:
                    acn = [n for n, _, _ in li.availableClaims]
                    self._printSuggestionPostAcceptLink(
                        self, acn, len(li.claimProofRequests))
                else:
                    self._printSyncAndAcceptUsage(li.name)
            else:
                self._printMoreThanOneLinkFoundMsg(linkName,
                                                   exactlyMatchedLinks,
                                                   likelyMatchedLinks)

            return True

    def _printNoClaimReqFoundMsg(self):
        self.print("No matching claim request(s) found in current keyring")

    def _printNoClaimFoundMsg(self):
        self.print("No matching claim(s) found in any links in current keyring")

    def _printMoreThanOneLinkFoundForRequest(self, requestedName, linkNames):
        self.print('More than one link matches "{}"'.format(requestedName))
        for li in linkNames:
            self.print("{}".format(li))
        # TODO: Any suggestion in more than one link?

    # TODO: Refactor following three methods
    # as most of the pattern looks similar

    def _printMoreThanOneClaimFoundForRequest(self, claimName, linkAndClaimNames):
        self.print('More than one match for "{}"'.format(claimName))
        for li, cl in linkAndClaimNames:
            self.print("{} in {}".format(li, cl))

    def _getOneLinkAndClaimReq(self, claimReqName) -> \
            (Link, ClaimProofRequest):
        matchingLinksWithClaimReq = self.activeWallet.\
            getMatchingLinksWithClaimReq(claimReqName)

        if len(matchingLinksWithClaimReq) == 0:
            self._printNoClaimReqFoundMsg()
            return None, None

        if len(matchingLinksWithClaimReq) > 1:
            linkNames = [ml.name for ml, cr in matchingLinksWithClaimReq]
            self._printMoreThanOneLinkFoundForRequest(claimReqName, linkNames)
            return None, None

        return matchingLinksWithClaimReq[0]

    def _getOneLinkAndAvailableClaim(self, claimName, printMsgs:bool=True) -> \
            (Link, ClaimDef):
        matchingLinksWithAvailableClaim = self.activeWallet.\
            getMatchingLinksWithAvailableClaim(claimName)

        if len(matchingLinksWithAvailableClaim) == 0:
            if printMsgs:
                self._printNoClaimFoundMsg()
            return None, None

        if len(matchingLinksWithAvailableClaim) > 1:
            linkNames = [ml.name for ml, _ in matchingLinksWithAvailableClaim]
            if printMsgs:
                self._printMoreThanOneLinkFoundForRequest(claimName, linkNames)
            return None, None

        return matchingLinksWithAvailableClaim[0]

    def _getOneLinkAndReceivedClaim(self, claimName, printMsgs:bool=True) -> \
            (Link, Tuple, Dict):
        matchingLinksWithRcvdClaim = self.activeWallet.\
            getMatchingLinksWithReceivedClaim(claimName)

        if len(matchingLinksWithRcvdClaim) == 0:
            if printMsgs:
                self._printNoClaimFoundMsg()
            return None, None, None

        if len(matchingLinksWithRcvdClaim) > 1:
            linkNames = [ml.name for ml, _, _ in matchingLinksWithRcvdClaim]
            if printMsgs:
                self._printMoreThanOneLinkFoundForRequest(claimName, linkNames)
            return None, None, None

        return matchingLinksWithRcvdClaim[0]

    def _setAttr(self, matchedVars):
        if matchedVars.get('set_attr') == 'set':
            attrName = matchedVars.get('attr_name')
            attrValue = matchedVars.get('attr_value')
            curLink, curClaimReq, selfAttestedAttrs = self.curContext
            if curClaimReq:
                selfAttestedAttrs[attrName] = attrValue
            else:
                self.print("No context, use below command to set the context")
                self._printShowClaimReqUsage()

            return True

    def _reqClaim(self, matchedVars):
        if matchedVars.get('req_claim') == 'request claim':
            claimName = SovrinCli.removeDoubleQuotes(
                matchedVars.get('claim_name'))
            matchingLink, ac = \
                self._getOneLinkAndAvailableClaim(claimName, printMsgs=False)
            if matchingLink:
                name, version, origin = ac
                if SovrinCli.isNotMatching(claimName, name):
                    self.print('Expanding {} to "{}"'.format(
                        claimName, name))
                self.print("Found claim {} in link {}".
                           format(claimName, matchingLink.name))
                if not self._isConnectedToAnyEnv():
                    self._printNotConnectedEnvMessage()
                    return True
                claimDefKey = (name, version, origin)
                getCredDefIsrKeyAndExecuteCallback(self.activeWallet,
                                                   self.activeClient,
                                                   self.print,
                                                   self.looper.loop,
                                                   claimDefKey,
                                                   self.sendReqClaim,
                                                   pargs=(matchingLink,
                                                          claimDefKey))
            else:
                self.print("No matching claim(s) found "
                           "in any links in current keyring")
            return True

    def _sendClaim(self, matchedVars):
        if matchedVars.get('send_claim') == 'send claim':
            claimName = matchedVars.get('claim_name').strip()
            linkName = matchedVars.get('link_name').strip()
            reqs = self.activeWallet.getMatchingLinksWithClaimReq(claimName)
            if not reqs:
                self._printNoClaimFoundMsg()
            elif len(reqs) > 1:
                self._printMoreThanOneLinkFoundForRequest(claimName, [(li, cr.name) for (li, cr) in reqs])
            else:
                links = self.activeWallet.getMatchingLinks(linkName)
                if not links:
                    self._printNoLinkFoundMsg()
                elif len(links) > 1:
                    self._printMoreThanOneLinkFoundMsg(linkName, {}, links)
                else:
                    link = links[0]
                    claimPrfReq = reqs[0][1]
                    proof, encodedAttrs, verifiableAttrs, claimDefKey = \
                        self.activeWallet.buildClaimProof(int(link.nonce, 16),
                                                          claimPrfReq)
                    _, curClaimReq, selfAttestedAttrs = self.curContext
                    for iid, attrs in encodedAttrs.items():
                        encodedAttrs[iid] = {n: str(v) for n, v in attrs.items()}
                    op = {
                        NAME: claimPrfReq.name,
                        VERSION: claimPrfReq.version,
                        NONCE: link.nonce,
                        TYPE: CLAIM_PROOF,
                        'proof': proof,
                        'encodedAttrs': encodedAttrs,
                        'verifiableAttrs': verifiableAttrs,
                        'selfAttestedAttrs': selfAttestedAttrs,
                        'claimDefKey': list(claimDefKey)
                    }
                    signature = self.activeWallet.signMsg(op, link.verkey)
                    op[f.SIG.nm] = signature
                    self._sendReqToTargetEndpoint(op, link)
            return True

    def _showReceivedOrAvailableClaim(self, claimName):
        self._showReceivedClaimIfExists(claimName) or \
            self._showAvailableClaimIfExists(claimName)

    def _printRequestClaimMsg(self, claimName):
        self.printSuggestion(self._getReqClaimUsage(claimName))

    def _showReceivedClaimIfExists(self, claimName):
        matchingLink, rcvdClaim, attributes = \
            self._getOneLinkAndReceivedClaim(claimName, printMsgs=False)
        if matchingLink:
            self.print("Found claim {} in link {}".
                       format(claimName, matchingLink.name))

            # TODO: Figure out how to get time of issuance
            self.print("Status: {}".format(datetime.datetime.now()))
            self.print('Name: {}\nVersion: {}'.format(claimName, rcvdClaim[1]))
            self.print("Attributes:")
            for n, v in attributes.items():
                self.print('    {}: {}'.format(n, v))
            self.print("")
            return rcvdClaim

    def _showAvailableClaimIfExists(self, claimName):
        matchingLink, ac = \
            self._getOneLinkAndAvailableClaim(claimName, printMsgs=False)
        if matchingLink:
            self.print("Found claim {} in link {}".
                       format(claimName, matchingLink.name))
            name, version, origin = ac
            claimDef = self.activeWallet.getClaimDef(key=ac)
            claimAttr = self.activeWallet.getClaimAttrs(ac)
            if claimAttr:
                #TODO: Figure out how to get time of issuance
                # self.print("Status: {}".format(ca.dateOfIssue))
                self.print("Status: {}".format(datetime.datetime.now()))
            else:
                self.print("Status: available (not yet issued)")

            if claimDef:
                self.print('Name: {}\nVersion: {}'.format(name, version))

            if not (claimAttr or claimDef):
                raise NotImplementedError
            else:
                self.print("Attributes:")

            attrs = []
            if not claimAttr:
                if claimDef:
                    attrs = [(n, '') for n in claimDef.attrNames]
            else:
                attrs = [(n, ': {}'.format(v)) for n, v in claimAttr.items()]
            if attrs:
                for n, v in attrs:
                    self.print('    {}{}'.format(n, v))

            if not claimAttr:
                self._printRequestClaimMsg(claimName)
            return ac
        else:
            self.print("No matching claim(s) found "
                       "in any links in current keyring")

    def _showMatchingClaimProof(self, claimProofReq: ClaimProofRequest, selfAttestedAttrs):
        matchingLinkAndRcvdClaims = \
            self.activeWallet.getMatchingRcvdClaims(claimProofReq.attributes)

        attributesWithValue = claimProofReq.attributes
        for k, v in claimProofReq.attributes.items():
            for ml, _, commonAttrs, allAttrs in matchingLinkAndRcvdClaims:
                if k in commonAttrs:
                    attributesWithValue[k] = allAttrs[k]
                else:
                    attributesWithValue[k] = selfAttestedAttrs.get(k, v)

        claimProofReq.attributes = attributesWithValue
        self.print(str(claimProofReq))

        for ml, (name, ver, _), commonAttrs, allAttrs in matchingLinkAndRcvdClaims:
            self.print('\n      Claim proof ({} v{} from {})'.format(
                name, ver, ml.name))
            for k, v in allAttrs.items():
                self.print('        ' + k + ': ' + v + ' (verifiable)')

    def _showClaimReq(self, matchedVars):
        if matchedVars.get('show_claim_req') == 'show claim request':
            claimReqName = SovrinCli.removeDoubleQuotes(
                matchedVars.get('claim_req_name'))
            matchingLink, claimReq = \
                self._getOneLinkAndClaimReq(claimReqName)
            if matchingLink and claimReq:
                if matchingLink == self.curContext[0] and claimReq == self.curContext[1]:
                    matchingLink, claimReq, attributes = self.curContext
                else:
                    attributes = {}
                    self.curContext = matchingLink, claimReq, attributes
                self.print('Found claim request "{}" in link "{}"'.
                           format(claimReq.name, matchingLink.name))
                self._showMatchingClaimProof(claimReq, attributes)
                self._printPostShowClaimReqSuggestion(claimReq.name,
                                                      matchingLink.name)
            return True

    def _showClaim(self, matchedVars):
        if matchedVars.get('show_claim') == 'show claim':
            claimName = SovrinCli.removeDoubleQuotes(
                matchedVars.get('claim_name'))
            self._showReceivedOrAvailableClaim(claimName)

            return True

    def _showFile(self, matchedVars):
        if matchedVars.get('show_file') == 'show':
            givenFilePath = matchedVars.get('file_path')
            filePath = SovrinCli._getFilePath(givenFilePath)
            if not filePath:
                self.print("Given file does not exist")
                self.printUsage(self._getShowFileUsage())
            else:
                with open(filePath, 'r') as fin:
                    self.print(fin.read())
                msgs = self._getLoadFileUsage(givenFilePath)
                self.printSuggestion(msgs)
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
                self.print("Connecting to {}...".format(envName), Token.BoldGreen)
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
            credDefKey = (credName, credVersion, self.activeWallet.defaultId)
            claimDef = self.activeWallet.getClaimDef(credDefKey)
            pk = self.activeWallet.getIssuerPublicKeyForClaimDef(claimDef.seqNo)
            attributes = self.attributeRepo.getAttributes(proverId).encoded()
            if attributes:
                attributes = list(attributes.values())[0]
            sk = CredDefSecretKey.fromStr(
                self.activeWallet.getClaimDefSk(claimDef.secretKey))
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
            self.print("Connected to {}.".format(self.activeEnv), Token.BoldBlue)
        else:
            self.looper.loop.call_later(.2, self.ensureClientConnected)

    def ensureAgentConnected(self, otherAgentHa, clbk: Callable=None,
                             *args):
        if not self.agent:
            return
        if self.agent.endpoint.isConnectedTo(ha=otherAgentHa):
            # TODO: Remove this print
            self.logger.debug("Agent {} connected to {}".
                              format(self.agent, otherAgentHa))
            if clbk:
                clbk(*args)
        else:
            self.looper.loop.call_later(.2, self.ensureAgentConnected,
                                        otherAgentHa, clbk, *args)

    def _ensureReqCompleted(self, reqId, client, clbk=None, pargs=None,
                            kwargs=None, cond=None, condPargs=None):
        ensureReqCompleted(self.looper.loop, reqId, client, clbk, pargs=pargs,
                           kwargs=kwargs, cond=cond, condPargs=condPargs)

    def addAlias(self, reply, err, client, alias, signer):
        if not self.canMakeSovrinRequest:
            return True

        txnId = reply[TXN_ID]
        op = {
            TARGET_NYM: alias,
            TXN_TYPE: NYM,
            # TODO: Should REFERENCE be symmetrically encrypted and the key
            # should then be disclosed in another transaction
            REF: txnId,
            ROLE: USER
        }
        self.print("Adding alias {}".format(alias), Token.BoldBlue)
        self.aliases[alias] = signer
        client.submit(op, identifier=self.activeSigner.identifier)

    def print(self, msg, token=None, newline=True):
        super().print(msg, token=token, newline=newline)

    def printHelp(self):
        self.print(
            """{}-CLI, a simple command-line interface for a {} sandbox.
    Commands:
        help - Shows this help message
        help <command> - Shows the help message of <command>
        new - creates one or more new nodes or clients
        keyshare - manually starts key sharing of a node
        status - Shows general status of the sandbox
        status <node_name>|<client_name> - Shows specific status
        list - Shows the list of commands you can run
        license - Show the license
        prompt <principal name> - Changes the prompt to <principal name>
        principals (a person like Alice, an organization like Faber College, or an IoT-style thing)
        load <invitation filename> - Creates the link, generates Identifier and signing keys
        show <invitation filename> - Shows the info about the link invitation
        show link <name> - Shows link info in case of one matching link, otherwise shows all the matching link <names>
        connect <{}> - Lets you connect to the respective environment
        sync <link name> - Synchronizes the link between the endpoints
        exit - exit the command-line interface ('quit' also works)
        """.format(self.properName, self.fullName, self.allEnvNames))

    def createFunctionMappings(self):
        from collections import defaultdict

        def promptHelper():
            self.print("Changes the prompt to provided principal name")
            self.printUsage(self._getPromptUsage())

        def principalsHelper():
            self.print("A person like Alice, "
                       "an organization like Faber College, "
                       "or an IoT-style thing")

        def loadHelper():
            self.print("Creates the link, generates Identifier and signing keys")
            self.printUsage(self._getLoadFileUsage("<invitation filename>"))

        def showHelper():
            self.print("Shows the info about the link invitation")
            self.printUsage(self._getShowFileUsage("<invitation filename>"))

        def showLinkHelper():
            self.print("Shows link info in case of one matching link, "
                       "otherwise shows all the matching links")
            self.printUsage(self._getShowLinkUsage())

        def connectHelper():
            self.print("Lets you connect to the respective environment")
            self.printUsage(self._getConnectUsage())

        def syncHelper():
            self.print("Synchronizes the link between the endpoints")
            self.printUsage(self._getSyncLinkUsage())

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

    @property
    def canMakeSovrinRequest(self):
        if not self.hasAnyKey:
            return False
        if not self.activeEnv:
            self._printNotConnectedEnvMessage()
            return False
        return True


class DummyClient:
    def submitReqs(self, *reqs):
        pass

    @property
    def hasSufficientConnections(self):
        pass
