import json
import os

import pytest

import sample
from plenum.common.txn import TYPE
from plenum.common.types import f
from plenum.common.util import randomString

from plenum.client.signer import SimpleSigner
from plenum.common.looper import Looper
from plenum.test.eventually import eventually
from plenum.test.helper import genHa, assertExp, assertFunc
from sovrin.agent.agent import WalletedAgent
from sovrin.agent.msg_types import ACCEPT_INVITE
from sovrin.client.client import Client
from sovrin.client.wallet.attribute import Attribute, LedgerStore
from sovrin.client.wallet.link import Link
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.txn import SPONSOR, NONCE, ENDPOINT
from sovrin.test.agent.acme import runAcme
from sovrin.test.agent.faber import runFaber
from sovrin.test.agent.helper import ensureAgentsConnected
from sovrin.test.helper import createNym, faberAddedClaimDefAndIssuerKeys, \
    addAttributeAndCheck


@pytest.fixture(scope="module")
def emptyLooper():
    with Looper() as l:
        yield l


@pytest.fixture(scope="module")
def faberWallet():
    name = "FaberCollege"
    wallet = Wallet(name)
    wallet.addSigner(signer=SimpleSigner(
        seed=b'Faber000000000000000000000000000'))
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
def aliceIsRunning(looper, aliceAgent):
    looper.add(aliceAgent)
    return aliceAgent


@pytest.fixture(scope="module")
def aliceAgentConnected(genned,
                        aliceAgent,
                        aliceIsRunning,
                        looper):
    looper.run(
        eventually(
            assertFunc, aliceAgent.client.isReady))
    return aliceAgent


@pytest.fixture(scope="module")
def faberAgentPort():
    return genHa()[1]


@pytest.fixture(scope="module")
def acmeAgentPort():
    return genHa()[1]


# @pytest.fixture(scope="module")
# def faberAdded(genned, looper, steward, stewardWallet, faberWallet):
#     createNym(looper, faberWallet.defaultId, steward, stewardWallet,
#               role=SPONSOR)


@pytest.fixture(scope="module")
def faberAdded(genned,
               steward,
               stewardWallet,
               looper,
               faberAgent):

    createNym(looper,
              faberAgent.wallet.defaultId,
              steward,
              stewardWallet,
              role=SPONSOR)

    ep = ':'.join(str(_) for _ in faberAgent.endpoint.ha)
    attributeData = json.dumps({ENDPOINT: ep})

    # TODO Faber Agent should be doing this!
    attrib = Attribute(name='test attribute',
                       origin=stewardWallet.defaultId,
                       value=attributeData,
                       dest=faberAgent.wallet.defaultId,
                       ledgerStore=LedgerStore.RAW)
    addAttributeAndCheck(looper, steward, stewardWallet, attrib)
    return attrib


@pytest.fixture(scope="module")
def faberAgent(tdirWithPoolTxns, faberAgentPort, faberWallet):
    agent = runFaber(faberWallet.name, faberWallet,
                     basedirpath=tdirWithPoolTxns,
                     port=faberAgentPort,
                     startRunning=False, bootstrap=False)
    return agent


@pytest.fixture(scope="module")
def faberIsRunning(emptyLooper, tdirWithPoolTxns, faberAgentPort,
                   faberWallet, faberAdded, faberAgent):
    faber = faberAgent
    faber.addKeyIfNotAdded()
    faberWallet.pendSyncRequests()
    prepared = faberWallet.preparePending()
    faber.client.submitReqs(*prepared)
    # faber.bootstrap()
    emptyLooper.add(faber)

    cdSeqNo, iskSeqNo = faberAddedClaimDefAndIssuerKeys(emptyLooper, faber)
    faber._seqNos = {
        ("Transcript", "1.2"): (cdSeqNo, iskSeqNo)
    }

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


@pytest.fixture(scope="module")
def faberNonceForAlice():
    return 'b1134a647eb818069c089e7694f63e6d'


@pytest.fixture(scope="module")
def acmeNonceForAlice():
    return '57fbf9dc8c8e6acde33de98c6d747b28c'


@pytest.fixture(scope="module")
def aliceAcceptedFaber(faberIsRunning, faberNonceForAlice, faberAdded,
                       aliceIsRunning, emptyLooper,
                       aliceInvitationLoaded,
                       aliceInvitationLinkSynced):
    """
    Faber creates a Link object, generates a link invitation file.
    Start FaberAgent
    Start AliceAgent and send a ACCEPT_INVITE to FaberAgent.
    """

    checkAcceptInvitation(emptyLooper,
                          faberNonceForAlice,
                          aliceIsRunning,
                          faberIsRunning,
                          linkName='Faber College')


@pytest.fixture(scope="module")
def faberInvitation():
    sampledir = os.path.dirname(sample.__file__)
    filename = os.path.join(sampledir, 'faber-invitation.sovrin')
    return filename


@pytest.fixture(scope="module")
def aliceInvitationLoaded(aliceAgent, faberInvitation):
    link = aliceAgent.loadInvitationFile(faberInvitation)
    assert link
    assert link.name == 'Faber College'
    return link


@pytest.fixture(scope="module")
def aliceInvitationLinkSynced(aliceInvitationLoaded,
                              aliceAgentConnected,
                              aliceAgent: WalletedAgent,
                              looper,
                              faberAdded
                              ):
    done = False

    def cb(reply, err):
        nonlocal done
        assert reply
        assert not err
        done = True

    def checkDone():
        assert done

    aliceAgent.sync(aliceInvitationLoaded.name, cb)
    looper.run(eventually(checkDone))

    link = aliceAgent.wallet.getLink('Faber College', required=True)
    assert link
    ep = link.remoteEndPoint
    assert ep
    assert len(ep) == 2


def checkAcceptInvitation(looper,
                          nonce,
                          userAgent: WalletedAgent,
                          agentIsRunning,
                          linkName):
    """
    Assumes link identified by linkName is already created
    """
    assert nonce
    agent, awallet = agentIsRunning
    a = agent  # type: WalletedAgent

    userAgent.connectTo(linkName)
    ensureAgentsConnected(looper, userAgent, agent)

    userAgent.acceptInvitation(linkName)

    internalId = a.getInternalIdByInvitedNonce(nonce)

    def chk():
        link = a.wallet.getLinkByInternalId(internalId)
        assert link
        # if not link:
        #     raise RuntimeError("Link not found for internal ID {}".
        #                        format(internalId))
        assert link.remoteIdentifier == userAgent.wallet.defaultId
        assert link.remoteEndPoint[1] == userAgent.endpoint.ha[1]

    looper.run(eventually(chk))


