"""
Abbreviated verkey tests
    Add a nym (16 byte, base58) with an abbreviated verkey (‘~’ with 16 bytes, base58) (Form 3)
        { type: NYM, dest: <id3>, verkey: ~<16byte abbreviated key> }
    Retrieve the verkey.
        { type: GET_NYM, dest: <id3> }
    Verify a signature from this identifier
    Change a verkey for a nym with a full verkey.
        { type: NYM, dest: <id3>, verkey: <32byte ED25519 key> }
    Retrieve new verkey
        { type: GET_NYM, dest: <id3> }
    Verify a signature from this identifier with the new verkey
"""

import pytest

ni = pytest.mark.skip("Not yet implemented")


def testNewIdentifierInWalletIsDid(abbrevIdr):
    assert len(abbrevIdr) == 22


def testDefaultVerkeyIsAbbreviated(abbrevVerkey):
    assert len(abbrevVerkey) == 23
    assert abbrevVerkey[0] == '~'


@ni
def testRetrieveEmptyVerkey():
    """{ type: GET_NYM, dest: <id1> }"""
    raise NotImplementedError


