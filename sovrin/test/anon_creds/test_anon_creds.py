from charm.core.math.integer import randomPrime

from anoncreds.protocol.utils import encodeAttrs
from sovrin.common.txn import CRED_DEF
from plenum.common.txn import DATA, ORIGIN
from plenum.common.txn import TXN_TYPE
from sovrin.test.helper import genTestClient, submitAndCheck
from plenum.test.helper import genHa


def cryptoNumber(size: int = 100):
    return randomPrime(size)


credDef = dict(type="JC1",
               ha={'ip': "10.10.10.10", 'port': 7897},
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
    "postgrad": "False"}

attrNames = list(attributes.keys())


def testAnonCredFlow(looper, tdir, nodeSet,
                     issuerSigner, proverSigner, verifierSigner,
                     addedIPV):
    # 3 Sovrin clients acting as Issuer, Signer and Verifier
    issuer = genTestClient(nodeSet, tmpdir=tdir, peerHA=genHa)
    prover = genTestClient(nodeSet, tmpdir=tdir, peerHA=genHa)
    verifier = genTestClient(nodeSet, tmpdir=tdir, peerHA=genHa)
    # Adding signers
    issuer.signers[issuerSigner.identifier] = issuerSigner
    prover.signers[proverSigner.identifier] = proverSigner
    verifier.signers[verifierSigner.identifier] = verifierSigner
    # Issuer's attribute repository
    attrRepo = {
        proverSigner.identifier:
            {attr: "{}-value".format(attr) for attr in attrNames}
    }
    issuer.attrRepo = attrRepo
    name1 = "Qualifications"
    version1 = "1.0"
    issuer.credentialDefinitions = {(name1, version1): credDef}
    issuerId = 'issuer1'
    proverId = 'prover1'
    verifierId = 'verifier1'
    interactionId = 'LOGIN-1'
    # Issuer publishes credential definition to Sovrin ledger
    op = {
        ORIGIN: issuerSigner.verstr,
        TXN_TYPE: CRED_DEF,
        DATA: credDef
    }
    submitAndCheck(looper, issuer, op, identifier=issuerSigner.identifier)
    # Prover requests Issuer for credential (out of band)
    # Issuer issues a credential for prover
    cred = issuer.createCredential(proverId, name1, version1)
    # Prover intends to prove certain attributes to a Verifier
    proofId = 'proof1'
    # Verifier issues a nonce
    nonce = verifier.generateNonce(interactionId)
    prover.proofs[proofId]['nonce'] = nonce
    # Prover discovers Issuer's credential definition
    prover.credentialDefinitions = {(issuerId, attrNames): credDef}
    revealedAttrs = ["undergrad"]
    proof = prover.prepare_proof(cred, encodeAttrs(attrNames),
    revealedAttrs, nonce)
    prover.proofs[proofId] = proof
    # Verifier fetches the credential definition from ledger
    verifier.credentialDefinitions = {(issuerId, name1, version1): credDef}
    # Verifier verifies proof
    verified = verifier.verify_proof(proof, nonce, attrNames, revealedAttrs)
    assert verified

