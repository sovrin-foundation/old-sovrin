import pytest
from plenum.client.signer import SimpleSigner
from plenum.common.looper import Looper
from sovrin.agent.faber import runFaber
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.txn import SPONSOR
from sovrin.test.helper import createNym


@pytest.fixture(scope="module")
def emptyLooper():
    with Looper() as l:
        yield l


@pytest.fixture(scope="module")
def faberWallet():
    name = "Faber College"
    wallet = Wallet(name)
    return wallet


@pytest.fixture(scope="module")
def faberAdded(genned, looper, steward, stewardWallet):
    createNym(looper, faberWallet.defaultId, steward, stewardWallet,
              role=SPONSOR)


@pytest.fixture(scope="module")
def faberIsRunning(emptyLooper, tdirWithPoolTxns, faberWallet):
    faberWallet.addSigner(signer=SimpleSigner())
    faber = runFaber(faberWallet.name, faberWallet,
                     basedirpath=tdirWithPoolTxns, startRunning=False)
    emptyLooper.add(faber)
    return faber, faberWallet
