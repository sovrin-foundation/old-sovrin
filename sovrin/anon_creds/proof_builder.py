from abc import abstractmethod, abstractproperty


class Proof:
    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass


class PredicateProof:
    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass


class Credential:
    def __init__(self, *args, **kwargs):
        pass


class ProofBuilder:

    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    @abstractproperty
    def id(self):
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
    def setParams(self, *args, **kwargs):
        pass

    @abstractmethod
    def prepareProof(*args, **kwargs) -> Proof:
        pass

    @abstractmethod
    def prepareProofAsDict(*args, **kwargs) -> dict:
        pass

    @abstractmethod
    def prepareProofFromDict(*args, **kwargs) -> Proof:
        pass

    @abstractmethod
    def preparePredicateProof(self, *args, **kwargs) -> PredicateProof:
        pass





