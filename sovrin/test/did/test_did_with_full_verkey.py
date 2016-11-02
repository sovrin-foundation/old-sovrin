"""
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
"""
from plenum.common.signer_did import DidSigner
from plenum.test.eventually import eventually
from sovrin.common.identity import Identity
from sovrin.test.did.conftest import pf
from sovrin.test.did.helper import chkVerifyForRetrievedIdentity
from sovrin.test.helper import createNym


@pf
def didAddedWithFullVerkey(addedSponsor, looper, sponsor, sponsorWallet,
                          wallet, fullKeyIdr):
    """{ type: NYM, dest: <id1> }"""
    createNym(looper, fullKeyIdr, sponsor, sponsorWallet,
              verkey=wallet.getVerkey(fullKeyIdr))
    return wallet


@pf
def newFullKey(wallet, fullKeyIdr):
    newSigner = DidSigner(identifier=fullKeyIdr)
    wallet.updateSigner(fullKeyIdr, newSigner)
    assert newSigner.verkey == wallet.getVerkey(fullKeyIdr)
    return newSigner.verkey


@pf
def didUpdatedWithFullVerkey(didAddedWithFullVerkey, looper, sponsor,
                            sponsorWallet, fullKeyIdr, newFullKey, wallet):
    """{ type: NYM, dest: <id1>, verkey: <vk1> }"""
    idy = Identity(identifier=fullKeyIdr,
                   verkey=newFullKey)
    sponsorWallet.updateSponsoredIdentity(idy)
    # TODO: What if the request fails, there must be some rollback mechanism
    assert sponsorWallet.getSponsoredIdentity(fullKeyIdr).seqNo is None
    reqs = sponsorWallet.preparePending()
    sponsor.submitReqs(*reqs)

    def chk():
        assert sponsorWallet.getSponsoredIdentity(fullKeyIdr).seqNo is not None

    looper.run(eventually(chk, retryWait=1, timeout=5))
    return wallet


@pf
def newVerkeyFetched(didAddedWithFullVerkey, looper, sponsor, sponsorWallet,
                     fullKeyIdr, wallet):
    """{ type: GET_NYM, dest: <id1> }"""
    identity = Identity(identifier=fullKeyIdr)
    req = sponsorWallet.requestIdentity(identity,
                                        sender=sponsorWallet.defaultId)
    sponsor.submitReqs(req)

    def chk():
        assert sponsorWallet.getIdentity(fullKeyIdr).verkey == wallet.getVerkey(
            fullKeyIdr)

    looper.run(eventually(chk, retryWait=1, timeout=5))


def testAddDidWithVerkey(didAddedWithFullVerkey):
    pass


def testRetrieveFullVerkey(didAddedWithFullVerkey, looper, sponsor,
                            sponsorWallet, wallet, fullKeyIdr):
    """{ type: GET_NYM, dest: <id1> }"""
    identity = Identity(identifier=fullKeyIdr)
    req = sponsorWallet.requestIdentity(identity,
                                        sender=sponsorWallet.defaultId)
    sponsor.submitReqs(req)

    def chk():
        assert sponsorWallet.getIdentity(fullKeyIdr).verkey == wallet.getVerkey(
            fullKeyIdr)

    looper.run(eventually(chk, retryWait=1, timeout=5))
    chkVerifyForRetrievedIdentity(wallet, sponsorWallet, fullKeyIdr)


def testChangeVerkeyToNewVerkey(didUpdatedWithFullVerkey):
    pass


def testRetrieveChangedVerkey(newVerkeyFetched):
    pass


def testVerifySigWithChangedVerkey(didUpdatedWithFullVerkey, newVerkeyFetched,
                                   sponsorWallet, fullKeyIdr, wallet):
    chkVerifyForRetrievedIdentity(wallet, sponsorWallet, fullKeyIdr)
