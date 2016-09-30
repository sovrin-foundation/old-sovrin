import pytest


@pytest.mark.skipif(True, reason="Client no longer has reference to Isuuer, "
                                 "Prover and Verifier. Maybe we check whether "
                                 "classes like CredDef have concrete methods "
                                 "or abstract methods. But if that enough?")
def testAnonCredPlugin(steward):
    assert steward.id is not None
    assert steward.attributeRepo is None
