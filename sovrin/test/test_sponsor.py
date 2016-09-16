from typing import Tuple

import libnacl.secret
import pytest

from plenum.common.util import randomString
from sovrin.common.txn import NYM, IDPROOF, newTxn
from sovrin.test.helper import Scenario


@pytest.fixture(scope="module")
def sponsorWithAgentScenario(keySharedNodes, looper, tdir):
    s = Scenario(nodeSet=keySharedNodes,
                 looper=looper,
                 tmpdir=tdir)
    s.addAgent()
    s.addSponsor()
    s.actor = s.sponsor
    s.run(setupAndStart)
    return s


@pytest.fixture(scope="module")
def sponsorWithoutAgentScenario(keySharedNodes, looper, tdir):
    s = Scenario(nodeSet=keySharedNodes,
                 looper=looper,
                 tmpdir=tdir)
    s.agent = None
    s.addSponsor()
    s.actor = s.sponsor
    s.run(setupAndStart)
    return s


@pytest.fixture(scope="module")
def agentScenario(keySharedNodes, looper, tdir):
    s = Scenario(nodeSet=keySharedNodes,
                 looper=looper,
                 tmpdir=tdir)

    s.addAgent()
    s.addSponsor()

    s.actor = s.agent
    s.run(setupAndStart)
    return s

ShouldSkip = True


@pytest.mark.skipif(ShouldSkip, reason="Need to decide exact schema")
def testSponsorRegistersUser(sponsorWithAgentScenario):
    s = sponsorWithAgentScenario
    s.run(registersUser)


@pytest.mark.skipif(ShouldSkip, reason="Need to decide exact schema")
def testSponsorAddsUserEmail(sponsorWithAgentScenario):
    sponsorWithAgentScenario.run(
            addsUserEmail)


@pytest.mark.skipif(ShouldSkip, reason="Need to decide exact schema")
def testSponsorWithoutAgentRegistersUser(sponsorWithoutAgentScenario):
    s = sponsorWithoutAgentScenario
    s.run(registersUser)


# @pytest.mark.skipif(True, reason="Not sure about the add agent transaction")
# def testSponsorWithoutAgentAssignsAgent(sponsorWithoutAgentScenario):
#     s = sponsorWithoutAgentScenario
#     s.ensureRun(registersUser)
#     s.run(assignAgent)


@pytest.mark.skipif(ShouldSkip, reason="Need to decide exact schema")
def testSponsorWithoutAgentAddsUserEmail(sponsorWithoutAgentScenario):
    sponsorWithoutAgentScenario.run(addsUserEmail)


@pytest.mark.skipif(ShouldSkip, reason="Need to decide exact schema")
def testAgentRegistersUser(agentScenario):
    agentScenario.run(registersUser)


@pytest.mark.skipif(ShouldSkip, reason="Need to decide exact schema")
def testAgentAddsUserEmail(agentScenario):
    agentScenario.run(addsUserEmail)


@pytest.mark.skipif(ShouldSkip, reason="Need to decide exact schema")
def testSponsorRegistersUserUsingAgentApi(nodeSet, looper, tdir):
    # Sponsor not on the blockchain, but is using an Agent's API
    with Scenario(nodeSet=nodeSet,
                  looper=looper,
                  tmpdir=tdir) as s:
        # TODO: Should the `Agent` class be used here? Or should `Organization` have a webserver?.
        # TODO: Need a webserver which is running on the agent
        s.addAgent()
        s.actor = s.agent

    # Test case: Sponsor creates a user, then assigns that user an agent

    # Test case: Sponsor on the blockchain, but is using an Agent's API

    # Test case: Sponsor not on the blockchain, but is using an Agent's API
        # agent creates user on the blockchain for sponsor
        # agent creates a wallet for the sponsor
        # agent has an API that the sponsor calls to create a user
        # agent creates the user wallet and creates the user on the blockchain
        # agent assigns himself as the user's agent and the sponsor as the user's sponsor


async def registersUser(s: Scenario):

    # await setupAndStart(s)

    # TODO Find out what attribute is added to the member wallet for the NYM transaction.
    # How does the correlation between userNym and sponsorNym happen for the member. Same for sponsor

    # createNymSMsg = self.getSignedReq(NYM, userNym, s.sponsor, agent=s.agent)
    # idProofSMsg = self.getSignedReq(IDPROOF, userNym, s.sponsor, agent=s.agent, data={'data': 42})

    origin = s.agentNym if s.agent else s.sponsorNym
    createNymReq = newTxn(txnType=NYM,
                          target=s.userNym,
                          origin=origin)

    idProofReq = newTxn(txnType=IDPROOF,
                        origin=origin,
                        target=s.userNym,
                        data={'data': 42})

    createNymReq = await s.send(createNymReq)
    idProofReq = await s.send(idProofReq)
    await s.checkAcks(count=2)
    await s.checkReplies([createNymReq, idProofReq])

async def setupAndStart(s: Scenario):
    # TODO: Should be an api call. But to which server does the api call go to?
    # Do we create a new server for the api?

    # Wallet is created by the Agent one time, but cryptonyms can be
    # created many times. The agent provides the cyptonym to the Sponsor
    s.agentNym = s.agent.wallet.newCryptonym() if s.agent else None
    s.sponsorNym = s.sponsor.wallet.newCryptonym() if s.agent else None

    # Created by the Sponsor on behalf of the member
    s.userId = "Ravi"
    s.actor.createUserWallet(s.userId)
    s.userNym = s.actor.getUserWallet(s.userId).newCryptonym()
    s.actor.getUserWallet(s.userId).addAgent(s.agentNym)

    await s.start()
    await s.startClient()


def getSymmetricallyEncryptedVal(val) -> Tuple[str, str]:
    if isinstance(val, str):
        val = val.encode("utf-8")
    box = libnacl.secret.SecretBox()
    return box.encrypt(val).hex(), box.sk.hex()


def getEncryptedEmail(userId=None):
    if not userId:
        userId = randomString(6)

    email = "{}@example.com".format(userId)
    encEmail, secretKey = getSymmetricallyEncryptedVal(email)
    return email, encEmail, secretKey


async def addsUserEmail(s: Scenario):

    # TODO It is the sponsor's responsibility to add a verified email. Right?
    email = "{}@example.com".format(s.userId)
    # TODO pool needs to verify signature (that every message is signed properly by the sender)
    # TODO need to add MAC authenticators of nodes

    s.actor.getUserWallet(s.userId).addAttribute(name="email", val=email, userNym=s.userNym,
                                                 sponsorNym=s.sponsorNym, agentNym=s.agentNym)


# async def assignAgent(s: Scenario):
#     s.addAgent()
#     s.agentNym = s.agent.wallet.newCryptonym()
#
#     op = txn(txnType=ASSIGN_AGENT,
#              targetNym=s.userNym,
#              sponsor=s.sponsorNym,
#              agent=s.agentNym)
#
#     req = await s.sendAndCheckAcks(op)
#
#     # TODO: Do we need the transaction id here? What if the actor(sponsor here) needs to verify that the agent was
#     # actually added?
#     result = await s.checkReplies(req)
#     txnId = result[0]['txnId']
#
#     s.actor.getUserWallet(s.userId).addAgent(s.agentNym)
#     return txnId
