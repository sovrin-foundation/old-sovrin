from abc import abstractmethod

from sovrin.anon_creds.cred_def import CredDefPublicKey, CredDef
from sovrin.anon_creds.proof_builder import ProofBuilder


class Prover:

    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def createProofBuilder(self, *args, **kwargs) -> ProofBuilder:
        pass

    # TODO: mention return type
    @abstractmethod
    def fetchNonce(self, *args, **kwargs):
        pass

    @abstractmethod
    def fetchCredentialDefinition(self, *args, **kwargs) -> CredDef:
        pass

    @abstractmethod
    def fetchCredential(self, *args, **kwargs):
        pass
