from abc import abstractmethod

from sovrin.anon_creds.cred_def import CredDefPublicKey, CredDef
from sovrin.anon_creds.issuer import Issuer
from sovrin.anon_creds.proof_builder import ProofBuilder
from sovrin.anon_creds.verifier import Verifier


class Prover:

    @abstractmethod
    def __init__(self, id):
        pass

    @abstractmethod
    def getPk(credDef: CredDef) -> CredDefPublicKey:
        pass

    @abstractmethod
    def createProofBuilder(self, issuer, attrNames, interactionId, verifier,
                           encodedAttrs, revealedAttrs) -> ProofBuilder:
        pass

    # TODO: mention return type
    @abstractmethod
    def fetchNonce(self, interactionId, verifier: Verifier):
        pass

    @abstractmethod
    def fetchCredentialDefinition(self, issuer: Issuer, attributes) -> CredDef:
        pass

    @abstractmethod
    def fetchCredential(self, issuer: Issuer, credName, credVersion, U):
        pass
