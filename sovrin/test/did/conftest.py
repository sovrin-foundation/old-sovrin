import pytest

from plenum.common.signer_simple import SimpleSigner
from sovrin.client.wallet.wallet import Wallet

pf = pytest.fixture(scope='module')


@pf
def wallet():
    return Wallet('my wallet')


@pf
def abbrevIdr(wallet):
    idr, _ = wallet.addIdentifier()
    return idr


@pf
def abbrevVerkey(wallet, abbrevIdr):
    return wallet.getVerkey(abbrevIdr)


@pf
def noKeyIdr(wallet):
    return wallet.addIdentifier(signer=SimpleSigner())[0]
