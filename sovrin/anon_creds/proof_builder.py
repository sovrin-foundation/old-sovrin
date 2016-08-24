from abc import abstractmethod, abstractproperty

from typing import Dict, Sequence, TypeVar

from sovrin.anon_creds.cred_def import CredDefPublicKey

class Proof:
    @abstractmethod
    def __init__(self, *args):
        pass


class PredicateProof:
    @abstractmethod
    def __init__(self, *args):
        pass

class Credential:
    def __init__(self, *args):
        pass


T = TypeVar('T')


class ProofBuilder:

    @abstractmethod
    def __init__(self, *args):
        pass

    @abstractproperty
    def masterSecret(self):
        pass

    @abstractproperty
    def U(self):
        pass

    @abstractproperty
    def vprime(self):
        pass

    @abstractmethod
    def setParams(self, credential, revealedAttrs, nonce):
        pass

    @abstractmethod
    def prepareProof(credDefPks, masterSecret, creds: Dict[str, Credential],
                     encodedAttrs: Dict[str, Dict[str, T]], revealedAttrs: Sequence[str],
                     nonce) -> Proof:
        pass

    @abstractmethod
    def preparePredicateProof(self, creds: Dict[str, Credential],
                              attrs: Dict[str, Dict[str, T]],
                              revealedAttrs: Sequence[str],
                              nonce, predicate: Dict[str, Dict]) -> PredicateProof:
        pass



