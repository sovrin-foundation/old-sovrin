import pytest
from plenum.common.util import randomString

from plenum.client.signer import SimpleSigner
from plenum.common.looper import Looper
from plenum.test.helper import genHa
from sovrin.agent.agent import WalletedAgent
from sovrin.client.client import Client
from sovrin.client.wallet.link import Link
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.txn import SPONSOR
from sovrin.test.agent.acme import runAcme
from sovrin.test.agent.faber import runFaber
from sovrin.test.helper import createNym


@pytest.fixture(scope="module")
def emptyLooper():
    with Looper() as l:
        yield l


@pytest.fixture(scope="module")
def faberWallet():
    name = "FaberCollege"
    wallet = Wallet(name)
    return wallet


@pytest.fixture(scope="module")
def walletBuilder():
    def _(name):
        wallet = Wallet(name)
        wallet.addSigner(signer=SimpleSigner())
        return wallet
    return _


@pytest.fixture(scope="module")
def aliceWallet(walletBuilder):
    return walletBuilder("Alice")


@pytest.fixture(scope="module")
def acmeWallet():
    name = "Acme"
    wallet = Wallet(name)
    return wallet


@pytest.fixture(scope="module")
def faberAdded(genned, looper, steward, stewardWallet, faberWallet):
    createNym(looper, faberWallet.defaultId, steward, stewardWallet,
              role=SPONSOR)


@pytest.fixture(scope="module")
def acmeAdded(genned, looper, steward, stewardWallet, acmeWallet):
    createNym(looper, acmeWallet.defaultId, steward, stewardWallet,
              role=SPONSOR)


@pytest.fixture(scope="module")
def agentBuilder(tdirWithPoolTxns):
    def _(wallet, basedir=None):
        basedir = basedir or tdirWithPoolTxns
        _, port = genHa()
        _, clientPort = genHa()
        client = Client(randomString(6),
                        ha=("0.0.0.0", clientPort),
                        basedirpath=basedir)

        agent = WalletedAgent(name=wallet.name,
                              basedirpath=basedir,
                              client=client,
                              wallet=wallet,
                              port=port)

        return agent
    return _


@pytest.fixture(scope="module")
def aliceAgent(aliceWallet, agentBuilder):
    return agentBuilder(aliceWallet)


@pytest.fixture(scope="module")
def aliceIsRunning(emptyLooper, aliceAgent):
    emptyLooper.add(aliceAgent)
    return aliceAgent


@pytest.fixture(scope="module")
def faberAgentPort():
    return genHa()[1]


@pytest.fixture(scope="module")
def acmeAgentPort():
    return genHa()[1]


@pytest.fixture(scope="module")
def faberIsRunning(emptyLooper, tdirWithPoolTxns, faberAgentPort,
                   faberWallet):
    faberWallet.addSigner(signer=SimpleSigner(
        seed=b'Faber000000000000000000000000000'))
    faber = runFaber(faberWallet.name, faberWallet,
                     basedirpath=tdirWithPoolTxns,
                     port=faberAgentPort,
                     startRunning=False, bootstrap=False)
    faber.addKeyIfNotAdded()
    faberWallet.pendSyncRequests()
    prepared = faberWallet.preparePending()
    faber.client.submitReqs(*prepared)
    # faber.bootstrap()
    emptyLooper.add(faber)
    return faber, faberWallet


@pytest.fixture(scope="module")
def acmeIsRunning(emptyLooper, tdirWithPoolTxns, acmeAgentPort,
                  acmeWallet):
    acmeWallet.addSigner(signer=SimpleSigner(
        seed=b'Acme0000000000000000000000000000'))
    acme = runAcme(acmeWallet.name, acmeWallet,
                     basedirpath=tdirWithPoolTxns,
                     port=acmeAgentPort,
                     startRunning=False)
    acmeWallet.pendSyncRequests()
    prepared = acmeWallet.preparePending()
    acme.client.submitReqs(*prepared)
    emptyLooper.add(acme)
    return acme, acmeWallet


# TODO: Rename it, not clear whether link is added to which wallet and
# who is adding
@pytest.fixture(scope="module")
def faberLinkAdded(faberIsRunning):
    # DEPR
    # faber, wallet = faberIsRunning
    # idr = wallet.defaultId
    # link = Link("Alice", idr, nonce="b1134a647eb818069c089e7694f63e6d")
    # wallet.addLink(link)
    # assert wallet.getMatchingLinks("Alice")
    # return link
    pass


@pytest.fixture(scope="module")
def acmeLinkAdded(acmeIsRunning):
    # DEPR
    # acme, wallet = acmeIsRunning
    # idr = wallet.defaultId
    # link = Link("Acme", idr, nonce="57fbf9dc8c8e6acde33de98c6d747b28c")
    # # TODO rename to addLink
    # wallet.addLink(link)
    # assert wallet.getMatchingLinks("Acme")
    # return link
    pass
