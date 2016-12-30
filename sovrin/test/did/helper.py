import base58
from plenum.common.signer_did import DidSigner
from plenum.common.verifier import DidVerifier
from plenum.test.eventually import eventually
from plenum.test.helper import assertEquality

from sovrin.common.identity import Identity

MsgForSigning = {'sender': 'Mario', 'msg': 'Lorem ipsum'}


def signMsg(wallet, idr):
    return wallet.signMsg(MsgForSigning, identifier=idr)


def verifyMsg(verifier, sig):
    sig = base58.b58decode(sig)
    return verifier.verifyMsg(sig, MsgForSigning)


def chkVerifyForRetrievedIdentity(signerWallet, verifierWallet, idr):
    sig = signMsg(signerWallet, idr)
    verkey = verifierWallet.getIdentity(idr).verkey
    assert verifyMsg(DidVerifier(verkey, idr), sig)


def updateWalletIdrWithFullKeySigner(wallet, idr):
    newSigner = DidSigner(identifier=idr)
    wallet.updateSigner(idr, newSigner)
    assertEquality(newSigner.verkey, wallet.getVerkey(idr))
    checkFullVerkeySize(wallet.getVerkey(idr))
    return newSigner.verkey


def updateSovrinIdrWithFullKey(looper, senderWallet, senderClient, ownerWallet,
                               idr, fullKey):
    idy = Identity(identifier=idr, verkey=fullKey)
    senderWallet.updateSponsoredIdentity(idy)
    # TODO: What if the request fails, there must be some rollback mechanism
    assert senderWallet.getSponsoredIdentity(idr).seqNo is None
    reqs = senderWallet.preparePending()
    senderClient.submitReqs(*reqs)

    def chk():
        assert senderWallet.getSponsoredIdentity(idr).seqNo is not None

    looper.run(eventually(chk, retryWait=1, timeout=5))
    return ownerWallet


def fetchFullVerkeyFromSovrin(looper, senderWallet, senderClient, ownerWallet,
                               idr):
    identity = Identity(identifier=idr)
    req = senderWallet.requestIdentity(identity, sender=senderWallet.defaultId)
    senderClient.submitReqs(req)

    def chk():
        retrievedVerkey = senderWallet.getIdentity(idr).verkey
        assertEquality(retrievedVerkey, ownerWallet.getVerkey(idr))
        checkFullVerkeySize(retrievedVerkey)
    looper.run(eventually(chk, retryWait=1, timeout=5))


def checkAbbrVerkeySize(verkey):
    # A base58 encoding of 32 bytes string can be either 44 bytes or 43 bytes,
    # since the did takes first 22 bytes,  abbreviated verkey will take
    # remaining 22 or 21 characters
    assert len(verkey) == 23 or len(verkey) == 22


def checkFullVerkeySize(verkey):
    # A base58 encoding of 32 bytes string can be either 44 bytes or 43 bytes.
    assert len(verkey) == 44 or len(verkey) == 43
