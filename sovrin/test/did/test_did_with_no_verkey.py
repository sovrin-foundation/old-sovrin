"""
Empty verkey tests
    Add a nym (16 byte, base58) without a verkey (Form 2).
        { type: NYM, dest: <id1> }
    Retrieve the verkey.
        { type: GET_NYM, dest: <id1> }
    Change verkey to new verkey (32 byte)
        { type: NYM, dest: <id1>, verkey: <vk1> }
    Retrieve new verkey
        { type: GET_NYM, dest: <id1> }
    Verify a signature from this identifier with the new verkey

Full verkey tests
    Add a nym (16 byte, base58) with a full verkey (32 byte, base58) (Form 1)
        { type: NYM, dest: <id2>, verkey: <32byte key> }
    Retrieve the verkey.
        { type: GET_NYM, dest: <id2> }
    Verify a signature from this identifier
    Change a verkey for a nym with a full verkey.
        { type: NYM, dest: <id2>, verkey: <32byte ED25519 key> }
    Retrieve new verkey
        { type: GET_NYM, dest: <id2> }
    Verify a signature from this identifier with the new verkey

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

DID Objects tests
    Store a DID object
    Retrieve a DID object
    Change a whole DID object
    Update just a portion of a DID object

DID forms tests
    Allow for identifiers that have the ‘did:sovrin:’ prefix
        did:sovrin:<16 byte, base58>
        Don’t store the prefix
    Allow for identifiers that omit the ‘did:sovrin:’ prefix
        <16 byte, base58>
    Allow for legacy cryptonyms
        Test that a 32-byte identifier is assumed to be a cryptonym, and the first 16 bytes are the identifier, and the last 16 bytes are the abbreviated verkey, and it is stored that way
    Any other forms are rejected.
"""

import pytest
from plenum.test.eventually import eventually
from sovrin.common.identity import Identity
from sovrin.test.did.conftest import pf
from sovrin.test.helper import addUser

ni = pytest.mark.skip("Not yet implemented")

@pf
def didAddedWithoutVerkey(addedSponsor, looper, sponsor, sponsorWallet):
    """{ type: NYM, dest: <id1> }"""
    return addUser(looper, sponsor, sponsorWallet, 'userA')


def testWalletCanProvideAnIdentifierWithoutAKey(wallet, noKeyIdr):
    # TODO, Question: Why would `getVerkey` return `None` for a CID, it should
    # be the CID itself.
    assert wallet.getVerkey(noKeyIdr) == noKeyIdr


def testAddDidWithoutAVerkey(didAddedWithoutVerkey):
    pass


def testRetrieveEmptyVerkey(didAddedWithoutVerkey, looper, sponsor,
                            sponsorWallet):
    """{ type: GET_NYM, dest: <id1> }"""
    addedNym = didAddedWithoutVerkey.defaultId
    identity = Identity(identifier=addedNym)
    req = sponsorWallet.requestIdentity(identity, sender=sponsorWallet.defaultId)
    sponsor.submitReqs(req)

    def chk():
        assert sponsorWallet.getIdentity(addedNym).verkey == addedNym

    looper.run(eventually(chk, retryWait=1, timeout=5))


def testChangeEmptyVerkeyToNewVerkey(didAddedWithoutVerkey, looper, sponsor,
                            sponsorWallet):
    """{ type: NYM, dest: <id1>, verkey: <vk1> }"""
    addedNym = didAddedWithoutVerkey.defaultId
    idy = sponsorWallet.getIdentity(addedNym).verkey == addedNym
    sponsorWallet.updateSponsoredIdentity(idy)
    reqs = sponsorWallet.preparePending()
    sponsor.submitReqs(*reqs)


@ni
def testRetrieveChangedVerkey():
    """{ type: GET_NYM, dest: <id1> }"""
    raise NotImplementedError


@ni
def testVerifySigWithChangedVerkey():
    raise NotImplementedError
