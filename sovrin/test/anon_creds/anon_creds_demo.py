import pprint
import shutil
import tempfile

from anoncreds.protocol.attribute_repo import AttributeRepo
from anoncreds.protocol.proof import Proof

from anoncreds.protocol.utils import encodeAttrs
from plenum.client.signer import SimpleSigner
from plenum.common.looper import Looper
from plenum.common.txn import DATA, ORIGIN
from plenum.common.txn import TXN_TYPE
from plenum.common.util import getlogger
from plenum.test.helper import genHa, ensureElectionsDone, \
    checkNodesConnected, genNodeReg

from sovrin.test.helper import genTestClient, submitAndCheck, createNym,\
    addNym, TestNodeSet
from sovrin.common.txn import CRED_DEF, SPONSOR
from sovrin.test.conftest import genesisTxns
from sovrin.test.anon_creds.helper import getCredDefTxnData

logger = getlogger()


attributes = {
    "first_name": "John",
    "last_name": "Doe",
    "birth_date": "1970-01-01",
    "expire_date": "2300-01-01",
    "undergrad": "True",
    "postgrad": "False"
}

attrNames = tuple(attributes.keys())

# TODO This hack makes the script incompatible with Windows.
shutil.rmtree('/tmp/data')
tdir = tempfile.TemporaryDirectory().name

stewardSigner = SimpleSigner()
sponsorSigner = SimpleSigner()
issuerSigner = SimpleSigner()
proverSigner = SimpleSigner()
verifierSigner = SimpleSigner()
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
    node.addGenesisTxns(genesisTxns(stewardSigner))

looper.run(checkNodesConnected(nodes))
ensureElectionsDone(looper=looper, nodes=nodes, retryWait=1, timeout=30)

steward = genTestClient(nodes, signer=stewardSigner, tmpdir=tdir)
whitelistClient(nodes, steward.name)
looper.add(steward)
looper.run(steward.ensureConnectedToNodes())
steward.requestPendingTxns()

createNym(looper, sponsorSigner, steward, stewardSigner, SPONSOR)

sponsor = genTestClient(nodes, signer=sponsorSigner, tmpdir=tdir)
whitelistClient(nodes, sponsor.name)
looper.add(sponsor)
looper.run(sponsor.ensureConnectedToNodes())


sponsNym = sponsorSigner.verstr
iNym = issuerSigner.verstr
pNym = proverSigner.verstr
vNym = verifierSigner.verstr
issuerHA = genHa()
proverHA = genHa()
verifierHA = genHa()

for nym, ha in ((iNym, issuerHA), (pNym, proverHA), (vNym, verifierHA)):
    addNym(ha, looper, nym, sponsNym, sponsor)


def runAnonCredFlow():
    # 3 Sovrin clients acting as Issuer, Signer and Verifier
    issuer = genTestClient(nodes, tmpdir=tdir, peerHA=genHa())
    prover = genTestClient(nodes, tmpdir=tdir, peerHA=genHa())
    verifier = genTestClient(nodes, tmpdir=tdir, peerHA=genHa())

    looper.add(issuer)
    looper.add(prover)
    looper.add(verifier)
    looper.run(issuer.ensureConnectedToNodes(),
               prover.ensureConnectedToNodes(),
               verifier.ensureConnectedToNodes())
    # Adding signers
    issuer.signers[issuerSigner.identifier] = issuerSigner
    input()
    logger.info("Key pair for Issuer created \n"
                "Public key is {} \n"
                "Private key is stored on disk\n".format(issuerSigner.verstr))
    prover.signers[proverSigner.identifier] = proverSigner
    input()
    logger.info("Key pair for Prover created \n"
                "Public key is {} \n"
                "Private key is stored on disk\n".format(proverSigner.verstr))
    verifier.signers[verifierSigner.identifier] = verifierSigner
    input()
    logger.info("Key pair for Verifier created \n"
                "Public key is {} \n"
                "Private key is stored on disk\n".format(
        verifierSigner.verstr))

    # Issuer's attribute repository
    attrRepo = AttributeRepo()
    attrRepo.attributes = {proverSigner.identifier: attributes}
    issuer.attributeRepo = attrRepo
    name1 = "Qualifications"
    version1 = "1.0"
    ip = issuer.peerHA[0]
    port = issuer.peerHA[1]
    issuerId = issuerSigner.identifier
    proverId = proverSigner.identifier
    verifierId = verifierSigner.identifier
    interactionId = 'LOGIN-1'

    # Issuer publishes credential definition to Sovrin ledger
    credDef = issuer.newCredDef(attrNames, name1, version1, ip=ip, port=port)
    # issuer.credentialDefinitions = {(name1, version1): credDef}
    input()
    logger.info("Issuer: Creating version {} of credential definition"
                " for {}".format(version1, name1))
    print("Credential definition: ")
    pprint.pprint(credDef)  # Pretty-printing the big object.
    op = {ORIGIN: issuerSigner.verstr, TXN_TYPE: CRED_DEF, DATA:
        getCredDefTxnData(credDef)}
    logger.info("Issuer: Writing credential definition to "
                "Sovrin Ledger...")
    submitAndCheck(looper, issuer, op, identifier=issuerSigner.identifier)

    # Prover requests Issuer for credential (out of band)
    input()
    logger.info("Prover: Requested credential from Issuer")
    # Issuer issues a credential for prover
    input()
    logger.info("Issuer: Creating credential for "
                "{}".format(proverSigner.verstr))

    encodedAttributes = {issuerId: encodeAttrs(attributes)}
    pk = {
        issuerId: prover.getPkFromCredDef(credDef)
    }
    proof = Proof(pk)
    proofId = proof.id
    prover.proofs[proofId] = proof
    cred = issuer.createCredential(proverId, name1, version1, proof.U[issuerId])
    input()
    logger.info("Prover: Received credential from "
                "{}".format(issuerSigner.verstr))

    # Prover intends to prove certain attributes to a Verifier
    # Verifier issues a nonce
    input()
    logger.info("Prover: Requesting Nonce from verifier…")
    logger.info("Verifier: Nonce received from prover"
                " {}".format(proverId))
    nonce = verifier.generateNonce(interactionId)
    input()
    logger.info("Verifier: Nonce sent.")
    input()
    logger.info("Prover: Nonce received")
    prover.proofs[proofId]['nonce'] = nonce

    presentationToken = {
        issuerId: (
            cred[0], cred[1],
            proof.vprime[issuerId] + cred[2])
    }
    # Prover discovers Issuer's credential definition
    prover.credentialDefinitions = {(issuerId, attrNames): credDef}
    revealedAttrs = ["undergrad"]
    input()
    logger.info("Prover: Preparing proof for attributes: "
                "{}".format(revealedAttrs))
    proof.setParams(encodedAttributes, presentationToken,
                    revealedAttrs, nonce)
    prf = proof.prepare_proof()
    logger.info("Prover: Proof prepared.")
    logger.info("Prover: Proof submitted")
    input()
    logger.info("Verifier: Proof received.")
    input()
    logger.info("Verifier: Looking up Credential Definition"
                " on Sovrin Ledger...")
    prover.proofs[proofId] = proof

    # Verifier fetches the credential definition from ledger
    verifier.credentialDefinitions = {
        (issuerId, name1, version1): credDef
    }
    # Verifier verifies proof
    logger.info("Verifier: Verifying proof...")
    verified = verifier.verify_proof(pk, prf, nonce,
                                     encodedAttributes,
                                     revealedAttrs)
    input()
    logger.info("Verifier: Proof verified.")
    assert verified
    input()
    logger.info("Prover: Proof accepted.")


if __name__ == "__main__":
    runAnonCredFlow()
