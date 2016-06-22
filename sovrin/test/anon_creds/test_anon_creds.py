import pprint

from anoncreds.protocol.utils import encodeAttrs
from plenum.common.txn import DATA, ORIGIN
from plenum.common.txn import TXN_TYPE
from plenum.common.util import getlogger
from plenum.test.helper import genHa
from sovrin.common.txn import CRED_DEF
from sovrin.test.anon_creds.helper import getCredDefTxnData
from sovrin.test.helper import genTestClient, submitAndCheck

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


def testAnonCredFlow(looper, tdir, nodeSet, issuerSigner, proverSigner,
                     verifierSigner, addedIPV):
    # 3 Sovrin clients acting as Issuer, Signer and Verifier
    issuer = genTestClient(nodeSet, tmpdir=tdir, signer=issuerSigner,
                           peerHA=genHa())
    prover = genTestClient(nodeSet, tmpdir=tdir, signer=proverSigner,
                           peerHA=genHa())
    verifier = genTestClient(nodeSet, tmpdir=tdir, signer=verifierSigner,
                             peerHA=genHa())

    looper.add(issuer)
    looper.add(prover)
    looper.add(verifier)
    looper.run(issuer.ensureConnectedToNodes(),
               prover.ensureConnectedToNodes(),
               verifier.ensureConnectedToNodes())
    # Adding signers
    issuer.signers[issuerSigner.identifier] = issuerSigner
    logger.info("Key pair for Issuer created \n"
                "Public key is {} \n"
                "Private key is stored on disk\n".format(issuerSigner.verstr))
    prover.signers[proverSigner.identifier] = proverSigner
    logger.info("Key pair for Prover created \n"
                "Public key is {} \n"
                "Private key is stored on disk\n".format(proverSigner.verstr))
    verifier.signers[verifierSigner.identifier] = verifierSigner
    logger.info("Key pair for Verifier created \n"
                "Public key is {} \n"
                "Private key is stored on disk\n".format(
                    verifierSigner.verstr))

    # Issuer's attribute repository
    attrRepo = {proverSigner.identifier: attributes}
    issuer.attrRepo = attrRepo
    name1 = "Qualifications"
    version1 = "1.0"
    ip = issuer.peerHA[0]
    port = issuer.peerHA[1]
    issuerId = 'issuer1'
    proverId = 'prover1'
    verifierId = 'verifier1'
    interactionId = 'LOGIN-1'

    # Issuer publishes credential definition to Sovrin ledger
    credDef = issuer.newCredDef(attrNames, name1, version1, ip=ip, port=port)
    # issuer.credentialDefinitions = {(name1, version1): credDef}
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
    logger.info("Prover: Requested credential from Issuer")
    # Issuer issues a credential for prover
    logger.info("Issuer: Creating credential for "
                "{}".format(proverSigner.verstr))
    cred = issuer.createCredential(proverId, name1, version1)
    logger.info("Prover: Received credential from "
                "{}".format(issuerSigner.verstr))

    # Prover intends to prove certain attributes to a Verifier
    proofId = 'proof1'

    # Verifier issues a nonce
    logger.info("Prover: Requesting Nonce from verifier…")
    logger.info("Verifier: Nonce received from prover"
                " {}".format(proverId))
    nonce = verifier.generateNonce(interactionId)
    logger.info("Verifier: Nonce sent.")
    logger.info("Prover: Nonce received")
    prover.proofs[proofId]['nonce'] = nonce

    # Prover discovers Issuer's credential definition
    prover.credentialDefinitions = {(issuerId, attrNames): credDef}
    revealedAttrs = ["undergrad"]
    logger.info("Prover: Preparing proof for attributes: "
                "{}".format(revealedAttrs))
    logger.info("Prover: Proof prepared.")
    proof = prover.prepare_proof(cred, encodeAttrs(attrNames),
                                 revealedAttrs, nonce)
    logger.info("Prover: Proof submitted")
    logger.info("Verifier: Proof received.")
    logger.info("Verifier: Looking up Credential Definition"
                " on Sovrin Ledger...")
    prover.proofs[proofId] = proof

    # Verifier fetches the credential definition from ledger
    verifier.credentialDefinitions = {
        (issuerId, name1, version1): credDef
    }

    # Verifier verifies proof
    logger.info("Verifier: Verifying proof...")
    verified = verifier.verify_proof(proof, nonce,
                                     attrNames, revealedAttrs)
    logger.info("Verifier: Proof verified.")
    assert verified
    logger.info("Prover: Proof accepted.")
