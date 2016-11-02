import base58

MsgForSigning = {'sender': 'Mario', 'msg': 'Lorem ipsum'}


def signMsg(wallet, idr):
    return wallet.signMsg(MsgForSigning, identifier=idr)


def verifyMsg(verifier, sig):
    sig = base58.b58decode(sig)
    return verifier.verifyMsg(sig, MsgForSigning)
