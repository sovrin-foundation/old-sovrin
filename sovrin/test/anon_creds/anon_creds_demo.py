import os
import pprint

from charm.core.math.integer import randomPrime

from anoncreds.protocol.utils import encodeAttrs
from plenum.client.signer import SimpleSigner
from plenum.common.looper import Looper
from plenum.common.txn import DATA, ORIGIN
from plenum.common.txn import TXN_TYPE
from plenum.common.util import getlogger
from plenum.test.helper import genHa, ensureElectionsDone, \
    checkNodesConnected, genNodeReg
from sovrin.common.txn import CRED_DEF, SPONSOR
from sovrin.test.helper import genTestClient, submitAndCheck, createNym,\
    addNym, TestNodeSet
from random import randint

from test.conftest import genesisTxns

logger = getlogger()


def cryptoNumber(bitLength: int = 100):
    return randomPrime(bitLength)


credDef = dict(type="JC1",
               ha={'ip': "10.10.10.10",
                   'port': 7897},
               keys={
                   "master_secret": cryptoNumber(),
                   "n": cryptoNumber(),
                   "S": cryptoNumber(),
                   "Z": cryptoNumber(),
                   "attributes": {
                       "first_name": cryptoNumber(),
                       "last_name": cryptoNumber(),
                       "birth_date": cryptoNumber(),
                       "expire_date": cryptoNumber(),
                       "undergrad": cryptoNumber(),
                       "postgrad": cryptoNumber(),
                   }
               })

attributes = {
    "first_name": "John",
    "last_name": "Doe",
    "birth_date": "1970-01-01",
    "expire_date": "2300-01-01",
    "undergrad": "True",
    "postgrad": "False"
}

attrNames = list(attributes.keys())


# TODO This isn't Windows compatible
def tdir():
    return os.path.join("/tmp",
                        str(randint(1000, 2000)))


stewardSigner = SimpleSigner()
sponsorSigner = SimpleSigner()
issuerSigner = SimpleSigner()
proverSigner = SimpleSigner()
verifierSigner = SimpleSigner()
nodes = TestNodeSet(nodeReg=genNodeReg(count=4), tmpdir=tdir(),
                     primaryDecider=None)
steward = genTestClient(nodes, signer=stewardSigner, tmpdir=tdir())
sponsor = genTestClient(nodes, signer=sponsorSigner, tmpdir=tdir())
looper = Looper(nodes, autoStart=True)
for node in nodes:
    node.startKeySharing()
    node.start(looper)
    node.addGenesisTxns(genesisTxns(stewardSigner))
    node.whitelistClient(steward.name)
    node.whitelistClient(sponsor.name)
looper.run(checkNodesConnected(nodes))
ensureElectionsDone(looper=looper, nodes=nodes, retryWait=1, timeout=30)
looper.add(steward)
looper.add(sponsor)
looper.run(steward.ensureConnectedToNodes())
looper.run(sponsor.ensureConnectedToNodes())
createNym(looper, sponsorSigner, steward, stewardSigner, SPONSOR)

sponsNym = sponsorSigner.verstr
iNym = issuerSigner.verstr
pNym = proverSigner.verstr
vNym = verifierSigner.verstr
issuerHA = genHa
proverHA = genHa
verifierHA = genHa

for nym, ha in ((iNym, issuerHA), (pNym, proverHA), (vNym, verifierHA)):
    addNym(ha, looper, nym, sponsNym, sponsor)


def runAnonCredFlow():
    # 3 Sovrin clients acting as Issuer, Signer and Verifier
    issuer = genTestClient(nodes, tmpdir=tdir(), peerHA=genHa())
    prover = genTestClient(nodes, tmpdir=tdir(), peerHA=genHa())
    verifier = genTestClient(nodes, tmpdir=tdir(), peerHA=genHa())

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
    attrRepo = {proverSigner.identifier: attributes}
    issuer.attrRepo = attrRepo
    name1 = "Qualifications"
    version1 = "1.0"
    issuerId = 'issuer1'
    proverId = 'prover1'
    verifierId = 'verifier1'
    interactionId = 'LOGIN-1'

    # Issuer publishes credential definition to Sovrin ledger
    issuer.credentialDefinitions = {(name1, version1): credDef}
    input()
    logger.info("Issuer: Creating version {} of credential definition"
                " for {}".format(version1, name1))
    print("Credential definition: ")
    pprint.pprint(credDef)  # Pretty-printing the big object.
    op = {ORIGIN: issuerSigner.verstr, TXN_TYPE: CRED_DEF, DATA: credDef}
    input()
    logger.info("Issuer: Writing credential definition to " "Sovrin Ledger...")
    submitAndCheck(looper, issuer, op, identifier=issuerSigner.identifier)

    # Prover requests Issuer for credential (out of band)
    input()
    logger.info("Prover: Requested credential from Issuer")
    # Issuer issues a credential for prover
    input()
    logger.info("Issuer: Creating credential for "
                "{}".format(proverSigner.verstr))
    cred = issuer.createCredential(proverId, name1, version1)
    input()
    logger.info("Prover: Received credential from "
                "{}".format(issuerSigner.verstr))

    # Prover intends to prove certain attributes to a Verifier
    proofId = 'proof1'

    # Verifier issues a nonce
    input()
    logger.info("Prover: Requesting Nonce from verifier…")
    input()
    logger.info("Verifier: Nonce received from prover" " {}".format(proverId))
    nonce = verifier.generateNonce(interactionId)
    input()
    logger.info("Verifier: Nonce sent.")
    input()
    logger.info("Prover: Nonce received")
    prover.proofs[proofId]['nonce'] = nonce

    # Prover discovers Issuer's credential definition
    prover.credentialDefinitions = {(issuerId, attrNames): credDef}
    revealedAttrs = ["undergrad"]
    input()
    logger.info("Prover: Preparing proof for attributes: "
                "{}".format(revealedAttrs))
    input()
    logger.info("Prover: Proof prepared.")
    proof = prover.prepare_proof(cred, encodeAttrs(attrNames), revealedAttrs,
                                 nonce)
    input()
    logger.info("Prover: Proof submitted")
    input()
    logger.info("Verifier: Proof received.")
    input()
    logger.info("Verifier: Looking up Credential Definition"
                " on Sovrin Ledger...")
    prover.proofs[proofId] = proof

    # Verifier fetches the credential definition from ledger
    verifier.credentialDefinitions = {(issuerId, name1, version1): credDef}

    # Verifier verifies proof
    input()
    logger.info("Verifier: Verifying proof...")
    verified = verifier.verify_proof(proof, nonce, attrNames, revealedAttrs)
    input()
    logger.info("Verifier: Proof verified.")
    assert verified
    input()
    logger.info("Prover: Proof accepted.")


if __name__ == "__main__":
    runAnonCredFlow()
