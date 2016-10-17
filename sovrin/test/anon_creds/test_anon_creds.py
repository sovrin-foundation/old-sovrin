# The following setup of logging needs to happen before everything else
import pytest

from plenum.common.log import DISPLAY_LOG_LEVEL, setupLogging, \
    DemoHandler, getlogger
from plenum.test.eventually import eventually
from sovrin.client.wallet.claim_def import ClaimDef

from anoncreds.protocol.cred_def_secret_key import CredDefSecretKey
from anoncreds.test.conftest import staticPrimes


def out(logger, record, extra_cli_value=None):
    """
    Callback so that this cli can manage colors

    :param record: a log record served up from a custom handler
    :param extra_cli_value: the "cli" value in the extra dictionary
    :return:
    """
    logger.display(record.msg)

import logging
import pprint

from ioflo.aid.consoling import Console
from functools import partial

import sovrin.anon_creds.issuer as IssuerModule
import sovrin.anon_creds.prover as ProverModule
import sovrin.anon_creds.proof_builder as ProofBuilderModule
import sovrin.anon_creds.verifier as VerifierModule

from plenum.common.txn import DATA, TXN_TYPE
from plenum.test.helper import genHa
from sovrin.common.txn import CRED_DEF
from sovrin.common.util import getCredDefTxnData
from sovrin.test.helper import submitAndCheck, makePendingTxnsRequest

from sovrin.client.wallet.wallet import Wallet


# TODO: This test checks for things already checked in `test_anon_cred_cli.py`.
# It fails. Updated it a bit. Will come back to it after taking care of more
# pressing issues.

@pytest.mark.skipif(True, reason="Refactoring incomplete")
def testAnonCredFlow(nodeSet,
                     looper,
                     tdir,
                     issuerWallet: Wallet,
                     proverWallet: Wallet,
                     verifierWallet,
                     addedIPV):

    # Don't move the following import outside of this method, otherwise that
    # client class doesn't gets reloaded and it doesn't get updated with the
    # correct plugin class/methods and it gives an error.
    # (for permanent solution bug is created: #130181205)
    from sovrin.test.helper import genTestClient

    BYU = IssuerModule.AttribDef('BYU',
                                 [IssuerModule.AttribType("first_name", encode=True),
                                  IssuerModule.AttribType("last_name", encode=True),
                                  IssuerModule.AttribType("birth_date", encode=True),
                                  IssuerModule.AttribType("expire_date", encode=True),
                                  IssuerModule.AttribType("undergrad", encode=True),
                                  IssuerModule.AttribType("postgrad", encode=True)]
                                 )

    setupLogging(DISPLAY_LOG_LEVEL,
                 Console.Wordage.mute)
    logger = getlogger("test_anon_creds")
    logging.root.addHandler(DemoHandler(partial(out, logger)))
    logging.root.handlers = []

    attributes = BYU.attribs(
        first_name="John",
        last_name="Doe",
        birth_date="1970-01-01",
        expire_date="2300-01-01",
        undergrad="True",
        postgrad="False"
    )

    attrNames = tuple(attributes.keys())
    # 3 Sovrin clients acting as Issuer, Signer and Verifier
    issuerC, _ = genTestClient(nodeSet, tmpdir=tdir, peerHA=genHa(),
                               usePoolLedger=True)
    proverC, _ = genTestClient(nodeSet, tmpdir=tdir, peerHA=genHa(),
                               usePoolLedger=True)
    verifierC, _ = genTestClient(nodeSet, tmpdir=tdir, peerHA=genHa(),
                                 usePoolLedger=True)

    looper.add(issuerC)
    looper.add(proverC)
    looper.add(verifierC)
    looper.run(issuerC.ensureConnectedToNodes(),
               proverC.ensureConnectedToNodes(),
               verifierC.ensureConnectedToNodes())
    makePendingTxnsRequest(issuerC, issuerWallet)
    makePendingTxnsRequest(proverC, proverWallet)
    makePendingTxnsRequest(verifierC, verifierWallet)
    # Adding signers
    # issuer.signers[issuerSigner.identifier] = issuerSigner
    logger.display("Key pair for Issuer created \n"
                   "Public key is {} \n"
                   "Private key is stored on disk\n".
                   format(issuerWallet.defaultId))
    # prover.signers[proverSigner.identifier] = proverSigner
    logger.display("Key pair for Prover created \n"
                   "Public key is {} \n"
                   "Private key is stored on disk\n".
                   format(proverWallet.defaultId))
    # verifier.signers[verifierSigner.identifier] = verifierSigner
    logger.display("Key pair for Verifier created \n"
                   "Public key is {} \n"
                   "Private key is stored on disk\n".
                   format(verifierWallet.defaultId))

    # TODO BYU.name is used here instead of issuerSigner.identifier due to
    #  tight coupling in Attribs.encoded()
    issuerId = BYU.name
    proverId = proverWallet.defaultId
    # Issuer's attribute repository
    attrRepo = IssuerModule.InMemoryAttrRepo()
    attrRepo.attributes = {proverId: attributes}

    name1 = "Qualifications"
    version1 = "1.0"
    ip = issuerC.peerHA[0]
    port = issuerC.peerHA[1]
    interactionId = 'LOGIN-1'

    # This is the issuer entity
    issuer = IssuerModule.Issuer(issuerId, attrRepo)
    # issuer.attributeRepo = attrRepo
    # Issuer publishes credential definition to Sovrin ledger

    csk = CredDefSecretKey(*staticPrimes().get("prime1"))
    cskId = issuerWallet.addClaimDefSk(str(csk))
    credDef = ClaimDef(seqNo=None,
                       attrNames=attrNames,
                       name=name1,
                       version=version1,
                       origin=issuerWallet.defaultId,
                       secretKey=cskId)
    # credDef = issuer.addNewCredDef(attrNames, name1, version1,
    #                                p_prime="prime1", q_prime="prime1", ip=ip,
    #                                port=port)
    # issuer.credentialDefinitions = {(name1, version1): credDef}
    logger.display("Issuer: Creating version {} of credential definition"
                   " for {}".format(version1, name1))
    print("Credential definition: ")
    pprint.pprint(credDef.get())  # Pretty-printing the big object.
    pending = issuerWallet.addClaimDef(credDef)
    reqs = issuerWallet.preparePending()

    logger.display("Issuer: Writing credential definition to "
                   "Sovrin Ledger...")
    issuerC.submitReqs(*reqs)

    def chk():
        assert issuerWallet.getClaimDef((name1,
                                         version1,
                                         issuerWallet.defaultId)).seqNo is not None

    looper.run(eventually(chk, retryWait=.1, timeout=30))

    # submitAndCheck(looper, issuerC, issuerWallet, op)


    # Prover requests Issuer for credential (out of band)
    logger.display("Prover: Requested credential from Issuer")
    # Issuer issues a credential for prover
    logger.display("Issuer: Creating credential for "
                   "{}".format(proverWallet.defaultId))

    encodedAttributes = attributes.encoded()
    revealedAttrs = ["undergrad"]

    prover = ProverModule.Prover(proverId)
    pk = {
        issuerId: prover.getPk(credDef)
    }
    proofBuilder = ProofBuilderModule.ProofBuilder(pk)
    proofId = proofBuilder.id
    prover.proofBuilders[proofId] = proofBuilder
    cred = issuer.createCred(proverId, name1, version1,
                             proofBuilder.U[issuerId])
    logger.display("Prover: Received credential from "
                   "{}".format(issuerWallet.defaultId))

    # Prover intends to prove certain attributes to a Verifier
    # Verifier issues a nonce
    logger.display("Prover: Requesting Nonce from verifier…")
    logger.display("Verifier: Nonce received from prover"
                   " {}".format(proverId))

    verifierId = verifierWallet.defaultId
    verifier = VerifierModule.Verifier(verifierId)
    nonce = verifier.generateNonce(interactionId)
    logger.display("Verifier: Nonce sent.")
    logger.display("Prover: Nonce received")

    presentationToken = {
        issuerId: (
            cred[0], cred[1],
            proofBuilder.vprime[issuerId] + cred[2])
    }
    # Prover discovers Issuer's credential definition
    logger.display("Prover: Preparing proof for attributes: "
                   "{}".format(revealedAttrs))
    proofBuilder.setParams(presentationToken,
                    revealedAttrs, nonce)
    prf = ProofBuilderModule.ProofBuilder.prepareProof(
        credDefPks=proofBuilder.issuerPks,
        masterSecret=proofBuilder.masterSecret,
        creds=presentationToken,
        encodedAttrs=encodedAttributes,
        revealedAttrs=revealedAttrs,
        nonce=nonce)
    logger.display("Prover: Proof prepared.")
    logger.display("Prover: Proof submitted")
    logger.display("Verifier: Proof received.")
    logger.display("Verifier: Looking up Credential Definition"
                   " on Sovrin Ledger...")

    # Verifier fetches the credential definition from ledger
    verifier.credentialDefinitions = {
        (issuerId, name1, version1): credDef
    }
    verified = VerifierModule.Verifier.verifyProof(pk, prf, nonce,
                                                   attributes.encoded(),
                                                   revealedAttrs)
    # Verifier verifies proof
    logger.display("Verifier: Verifying proof...")
    logger.display("Verifier: Proof verified.")
    assert verified
    logger.display("Prover: Proof accepted.")

    # TODO: Reset the log level back to original.
