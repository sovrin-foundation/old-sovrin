from plenum.common.looper import Looper
from pytest import yield_fixture
from sovrin.common.txn import SPONSOR
from sovrin.test.helper import createNym


@yield_fixture(scope="module")
def emptyLooper():
    with Looper() as l:
        yield l


@yield_fixture(scope="module")
def faberAdded():
    createNym(looper, li.targetIdentifier, client, wallet, role=SPONSOR)