import base58
from plenum.common.verifier import DidVerifier

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
