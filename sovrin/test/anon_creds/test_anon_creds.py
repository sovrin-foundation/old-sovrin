import logging
import pprint
# The following setup of logging needs to happen before everything else
from plenum.common.util import getlogger, setupLogging, DISPLAY_LOG_LEVEL
from ioflo.aid.consoling import Console

logging.root.handlers = []
setupLogging(5,
             Console.Wordage.mute)
logger = getlogger("test_anon_creds")

from anoncreds.protocol.attribute_repo import AttributeRepo
from anoncreds.protocol.proof import Proof
from charm.core.math.integer import randomPrime

from anoncreds.protocol.utils import encodeAttrs
from plenum.common.txn import DATA, ORIGIN
from plenum.common.txn import TXN_TYPE
from plenum.test.helper import genHa
from sovrin.common.txn import CRED_DEF
from sovrin.test.anon_creds.helper import getCredDefTxnData
from sovrin.test.helper import genTestClient, submitAndCheck


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
    logger.display("Key pair for Issuer created \n"
                "Public key is {} \n"
                "Private key is stored on disk\n".format(issuerSigner.verstr))
    prover.signers[proverSigner.identifier] = proverSigner
    logger.display("Key pair for Prover created \n"
                "Public key is {} \n"
                "Private key is stored on disk\n".format(proverSigner.verstr))
    verifier.signers[verifierSigner.identifier] = verifierSigner
    logger.display("Key pair for Verifier created \n"
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
    logger.display("Issuer: Creating version {} of credential definition"
                " for {}".format(version1, name1))
    print("Credential definition: ")
    pprint.pprint(credDef.get())  # Pretty-printing the big object.
    op = {ORIGIN: issuerSigner.verstr, TXN_TYPE: CRED_DEF, DATA:
        getCredDefTxnData(credDef)}
    logger.display("Issuer: Writing credential definition to "
                "Sovrin Ledger...")
    submitAndCheck(looper, issuer, op, identifier=issuerSigner.identifier)

    # Prover requests Issuer for credential (out of band)
    logger.display("Prover: Requested credential from Issuer")
    # Issuer issues a credential for prover
    logger.display("Issuer: Creating credential for "
                "{}".format(proverSigner.verstr))

    encodedAttributes = {issuerId: encodeAttrs(attributes)}
    revealedAttrs = ["undergrad"]
    pk = {
        issuerId: prover.getPkFromCredDef(credDef)
    }
    proof = Proof(pk)
    proofId = proof.id
    prover.proofs[proofId] = proof
    cred = issuer.createCredential(proverId, name1, version1, proof.U[issuerId])
    logger.display("Prover: Received credential from "
                "{}".format(issuerSigner.verstr))

    # Prover intends to prove certain attributes to a Verifier
    # Verifier issues a nonce
    logger.display("Prover: Requesting Nonce from verifier…")
    logger.display("Verifier: Nonce received from prover"
                " {}".format(proverId))
    nonce = verifier.generateNonce(interactionId)
    logger.display("Verifier: Nonce sent.")
    logger.display("Prover: Nonce received")

    presentationToken = {
        issuerId: (
            cred[0], cred[1],
            proof.vprime[issuerId] + cred[2])
    }
    # Prover discovers Issuer's credential definition
    logger.display("Prover: Preparing proof for attributes: "
                "{}".format(revealedAttrs))
    proof.setParams(encodedAttributes, presentationToken,
                    revealedAttrs, nonce)
    prf = proof.prepare_proof()
    logger.display("Prover: Proof prepared.")
    logger.display("Prover: Proof submitted")
    logger.display("Verifier: Proof received.")
    logger.display("Verifier: Looking up Credential Definition"
                " on Sovrin Ledger...")

    # Verifier fetches the credential definition from ledger
    verifier.credentialDefinitions = {
        (issuerId, name1, version1): credDef
    }
    verified = verifier.verify_proof(pk, prf, nonce,
                                     encodedAttributes,
                                     revealedAttrs)
    # Verifier verifies proof
    logger.display("Verifier: Verifying proof...")
    logger.display("Verifier: Proof verified.")
    assert verified
    logger.display("Prover: Proof accepted.")
