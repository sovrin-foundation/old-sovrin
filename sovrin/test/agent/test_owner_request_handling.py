import pytest


@pytest.mark.skip("Not yet implemented")
def testUnsignedRequest():
    """
    Ensure an unsigned request is not allowed.
    """
    raise NotImplementedError


@pytest.mark.skip("Not yet implemented")
def testRequestSignedByUnknownIdentifier():
    """
    Ensure a request signed by an unknown party is not allowed.
    """
    raise NotImplementedError


@pytest.mark.skip("Not yet implemented")
def testRequestSignedByKnownIdentifier():
    """
    Ensure a properly signed request is allowed.
    """
    raise NotImplementedError
