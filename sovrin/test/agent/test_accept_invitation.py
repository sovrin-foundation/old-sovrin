import pytest
from plenum.client.signer import SimpleSigner
from plenum.common.util import randomString
from sovrin.agent.faber import runFaber
from sovrin.client.wallet.link_invitation import LinkInvitation
from sovrin.client.wallet.wallet import Wallet


@pytest.fixture(scope="module")
def faberIsRunning(emptyLooper, tdirWithPoolTxns):
    name = randomString()
    wallet = Wallet(name)
    wallet.addSigner(signer=SimpleSigner())
    faber = runFaber(name, wallet, basedirpath=tdirWithPoolTxns,
                     startRunning=False)
    emptyLooper.add(faber)
    return faber, wallet


def testFaberCreateLink(faberIsRunning):
    faber, wallet = faberIsRunning
    idr = wallet.defaultId
    # TODO rename to Link
    link = LinkInvitation("Alice", idr, wallet._getIdData().signer.verkey)
    wallet.addLinkInvitation(link)
    assert wallet.getMatchingLinkInvitations("Alice")


def testAcceptInvitation(faberIsRunning, aliceCLI, faberAdded):
    """
    Faber creates a Link object, generates a link invitation file.
    Create a cli for Alice with link invitation loaded and start FaberAgent
    and send a ACCEPT_INVITE from Alice's cli.
    """
    pass


def testAddClaimDef():
    pass


def testAddIssuerKeys():
    pass
