import logging
import os
import pprint
import shutil
import tempfile

# The following setup of logging needs to happen before everything else
from plenum.common.log import getlogger
from sovrin.anon_creds.cred_def import CredDef
from sovrin.anon_creds.issuer import InMemoryAttrRepo
from sovrin.anon_creds.proof_builder import ProofBuilder
from sovrin.anon_creds.verifier import Verifier

from plenum.common.txn_util import createGenesisTxnFile

logging.root.handlers = []
# setupLogging(DISPLAY_LOG_LEVEL,
#              Console.Wordage.mute)
logger = getlogger("anon_creds_demo")

from plenum.common.looper import Looper
from plenum.common.txn import DATA, ORIGIN
from plenum.common.txn import TXN_TYPE
from plenum.test.helper import genHa, ensureElectionsDone, \
    checkNodesConnected, genNodeReg

from sovrin.test.helper import genTestClient, submitAndCheck, createNym, \
    TestNodeSet, _newWallet, makePendingTxnsRequest
from sovrin.common.txn import CRED_DEF, SPONSOR, getTxnOrderedFields
from sovrin.test.conftest import genesisTxns
from sovrin.common.util import getCredDefTxnData, getConfig
import sovrin.anon_creds.issuer as IssuerModule
import sovrin.anon_creds.prover as ProverModule
import sovrin.anon_creds.verifier as VerifierModule


config = getConfig()


rawAttributes = {
    "first_name": "John",
    "last_name": "Doe",
    "birth_date": "1970-01-01",
    "expire_date": "2300-01-01",
    "undergrad": "True",
    "postgrad": "False"
}

attrNames = tuple(rawAttributes.keys())

attrTypes = [IssuerModule.AttribType(name, encode=True) for name in attrNames]
attrDefs = IssuerModule.AttribDef('BYU', attrTypes)
attributes = attrDefs.attribs(**rawAttributes)

dataDir = '/tmp/data'
if os.path.exists(dataDir):
    shutil.rmtree(dataDir)
tdir = tempfile.TemporaryDirectory().name

stewardWallet = _newWallet()
sponsorWallet = _newWallet()
issuerWallet = _newWallet()
proverWallet = _newWallet()
verifierWallet = _newWallet()

createGenesisTxnFile(genesisTxns(stewardWallet), tdir,
                             config.domainTransactionsFile,
                             getTxnOrderedFields())

nodes = TestNodeSet(nodeReg=genNodeReg(count=4), tmpdir=tdir,
        primaryDecider=None)


def whitelistClient(nodes, *clientNames):
    for node in nodes:
        for nm in clientNames:
            node.whitelistClient(nm)

looper = Looper(nodes, autoStart=True)
for node in nodes:
    node.startKeySharing()
    node.start(looper)
    # node.addGenesisTxns(genesisTxns(stewardSigner))

looper.run(checkNodesConnected(nodes))
ensureElectionsDone(looper=looper, nodes=nodes, retryWait=1, timeout=30)

steward, _ = genTestClient(nodes, tmpdir=tdir)
# whitelistClient(nodes, steward.name)
steward.registerObserver(stewardWallet.handleIncomingReply)
looper.add(steward)
looper.run(steward.ensureConnectedToNodes())
makePendingTxnsRequest(steward, stewardWallet)


createNym(looper, sponsorWallet.defaultId, steward, stewardWallet, SPONSOR)

sponsor, _ = genTestClient(nodes, tmpdir=tdir)
sponsor.registerObserver(sponsorWallet.handleIncomingReply)
# whitelistClient(nodes, sponsor.name)
looper.add(sponsor)
looper.run(sponsor.ensureConnectedToNodes())
makePendingTxnsRequest(sponsor, sponsorWallet)

iNym = issuerWallet.defaultId
pNym = proverWallet.defaultId
vNym = verifierWallet.defaultId


for nym in (iNym, pNym, vNym):
    createNym(looper, nym, sponsor, sponsorWallet)

issuerHA = genHa()
proverHA = genHa()
verifierHA = genHa()


def runAnonCredFlow():
    # 3 Sovrin clients acting as Issuer, Signer and Verifier
    issuerC, _ = genTestClient(nodes, tmpdir=tdir, peerHA=genHa())
    proverC, _ = genTestClient(nodes, tmpdir=tdir, peerHA=genHa())
    verifierC, _ = genTestClient(nodes, tmpdir=tdir, peerHA=genHa())

    looper.add(issuerC)
    looper.add(proverC)
    looper.add(verifierC)
    looper.run(issuerC.ensureConnectedToNodes(),
               proverC.ensureConnectedToNodes(),
               verifierC.ensureConnectedToNodes())
    # Adding signers
    # issuer.signers[issuerWallet.defaultId] = issuerSigner
    logger.display("Key pair for Issuer created \n"
                "Public key is {} \n"
                "Private key is stored on disk\n".format(issuerWallet.defaultId))
    # prover.signers[proverWallet.defaultId] = proverSigner
    input()
    logger.display("Key pair for Prover created \n"
                "Public key is {} \n"
                "Private key is stored on disk\n".format(proverWallet.defaultId))
    # verifier.signers[verifierWallet.defaultId] = verifierSigner
    input()
    logger.display("Key pair for Verifier created \n"
                "Public key is {} \n"
                "Private key is stored on disk\n".format(
        verifierWallet.defaultId))

    # Issuer's attribute repository
    attrRepo = InMemoryAttrRepo()
    attrRepo.attributes = {proverWallet.defaultId: attributes}
    # issuer.attributeRepo = attrRepo
    name1 = "Qualifications"
    version1 = "1.0"
    ip = issuerC.peerHA[0]
    port = issuerC.peerHA[1]
    issuerId = issuerWallet.defaultId
    proverId = proverWallet.defaultId
    verifierId = verifierWallet.defaultId
    interactionId = 'LOGIN-1'

    issuer = IssuerModule.Issuer(issuerId, attrRepo)
    # Issuer publishes credential definition to Sovrin ledger
    credDef = issuer.addNewCredDef(attrNames, name1, version1, ip=ip, port=port)
    # issuer.credentialDefinitions = {(name1, version1): credDef}
    input()
    logger.display("Issuer: Creating version {} of credential definition"
                " for {}".format(version1, name1))
    print("Credential definition: ")
    pprint.pprint(credDef.get())  # Pretty-printing the big object.
    input()
    op = {ORIGIN: issuerWallet.defaultId, TXN_TYPE: CRED_DEF, DATA:
        getCredDefTxnData(credDef)}
    logger.display("Issuer: Writing credential definition to "
                "Sovrin Ledger...")
    submitAndCheck(looper, issuer, op, identifier=issuerWallet.defaultId)

    # Prover requests Issuer for credential (out of band)
    input()
    logger.display("Prover: Requested credential from Issuer")
    # Issuer issues a credential for prover
    input()
    logger.display("Issuer: Creating credential for "
                "{}".format(proverWallet.defaultId))
    prover = ProverModule.Prover(proverId)

    encodedAttributes = {issuerId: CredDef.getEncodedAttrs(attributes)}
    pk = {
        issuerId: prover.getPk(credDef)
    }
    proofBuilder = ProofBuilder(pk)
    prover.proofBuilders[proofBuilder.id] = proofBuilder
    cred = issuer.createCred(proverId, name1, version1, proofBuilder.U[issuerId])
    input()
    logger.display("Prover: Received credential from "
                "{}".format(issuerWallet.defaultId))

    # Prover intends to prove certain attributes to a Verifier
    # Verifier issues a nonce
    input()
    logger.display("Prover: Requesting Nonce from verifier…")
    verifier = VerifierModule.Verifier(verifierId)
    logger.display("Verifier: Nonce received from prover"
                " {}".format(proverId))
    nonce = verifier.generateNonce(interactionId)
    input()
    logger.display("Verifier: Nonce sent.")
    input()
    logger.display("Prover: Nonce received")
    prover.proofBuilders[proofBuilder.id]['nonce'] = nonce

    # Prover discovers Issuer's credential definition
    prover.credentialDefinitions = {(issuerId, attrNames): credDef}
    revealedAttrs = ["undergrad"]
    input()
    logger.display("Prover: Preparing proof for attributes: "
                "{}".format(revealedAttrs))
    proofBuilder.setParams(encodedAttributes, revealedAttrs, nonce)
    prf = proofBuilder.prepareProof()
    logger.display("Prover: Proof prepared.")
    logger.display("Prover: Proof submitted")
    input()
    logger.display("Verifier: Proof received.")
    input()
    logger.display("Verifier: Looking up Credential Definition"
                " on Sovrin Ledger...")
    prover.proofs[proofBuilder.id] = proofBuilder

    # Verifier fetches the credential definition from ledger
    verifier.credentialDefinitions = {
        (issuerId, name1, version1): credDef
    }
    # Verifier verifies proof
    logger.display("Verifier: Verifying proof...")
    verified = Verifier.verifyProof(pk, prf, nonce,
                                     encodedAttributes,
                                     revealedAttrs)
    input()
    logger.display("Verifier: Proof verified.")
    assert verified
    input()
    logger.display("Prover: Proof accepted.")


if __name__ == "__main__":
    runAnonCredFlow()
