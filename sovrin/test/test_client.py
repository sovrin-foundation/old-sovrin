import random
from functools import partial

import pytest
from plenum.client.signer import SimpleSigner
from plenum.common.request_types import f
from plenum.test.eventually import eventually, eventuallyAll

from plenum.test.helper import checkReqAck

from sovrin.common.txn import ADD_ATTR, ADD_NYM, storedTxn, \
    STEWARD, TARGET_NYM, TXN_TYPE, ROLE, SPONSOR, ORIGIN, DATA, USER, IDPROOF
from sovrin.test.helper import genTestClient, genConnectedTestClient, \
    clientFromSigner


@pytest.fixture(scope="module")
def genesisTxns(stewardSigner):
    nym = stewardSigner.verstr
    return [storedTxn(ADD_NYM, nym,
                "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b",
                role=STEWARD),
        ]


# TODO use wallet instead of SimpleSigner in client


def checkNacks(client, reqId, contains='', nodeCount=4):

    reqs = [x for x, _ in client.inBox if x[f.REQ_ID.nm] == reqId]
    for r in reqs:
        assert r['op'] == 'REQNACK'
        assert f.REASON.nm in r
        assert contains in r[f.REASON.nm]
    assert len(reqs) == nodeCount


def submitAndCheck(looper, client, op):
    txnCount = len(client.getTxnsByAttribute(TXN_TYPE))

    client.submit(op)

    def checkTxnCountAdvanced():
        assert len(client.getTxnsByAttribute(TXN_TYPE)) == txnCount + 1

    looper.run(eventually(checkTxnCountAdvanced, retryWait=1, timeout=15))


def submitAndCheckNacks(looper, client, op,
                        contains='UnauthorizedClientRequest'):
    client.submit(op)
    looper.run(eventually(checkNacks,
                          client,
                          client.lastReqId,
                          contains))


def testNonStewardCannotCreateASponsor(steward, stewardSigner, looper, nodeSet):
    seed = b'this is a secret sponsor seed...'
    sponsorSigner = SimpleSigner('sponsor', seed)

    sponsorNym = sponsorSigner.verstr

    op = {
        ORIGIN: stewardSigner.verstr,
        TARGET_NYM: sponsorNym,
        TXN_TYPE: ADD_NYM,
        ROLE: SPONSOR
    }

    submitAndCheckNacks(looper, steward, op)


def createNym(looper, targetSigner, creatorClient, creatorSigner, role):
    nym = targetSigner.verstr
    op = {
        ORIGIN: creatorSigner.verstr,
        TARGET_NYM: nym,
        TXN_TYPE: ADD_NYM,
        ROLE: role
    }
    submitAndCheck(looper, creatorClient, op)
    return targetSigner


def addUser(looper, creatorClient, creatorSigner, name):
    usigner = SimpleSigner(name)
    return createNym(looper, usigner, creatorClient, creatorSigner, USER)


@pytest.fixture(scope="module")
def addedSponsor(genned, steward, stewardSigner, looper, sponsorSigner):
    return createNym(looper, sponsorSigner, steward, stewardSigner, SPONSOR)


def testStewardCreatesASponsor(addedSponsor):
    pass


@pytest.fixture(scope="module")
def anotherSponsor(genned, steward, stewardSigner, looper, sponsorSigner):
    return createNym(looper, sponsorSigner, steward, stewardSigner, SPONSOR)


def testStewardCreatesAnotherSponsor(genned, steward, stewardSigner, looper,
                               nodeSet, tdir, sponsorSigner):
    return createNym(looper, sponsorSigner, steward, stewardSigner, SPONSOR)


def testTxnRetrievalByAttributeName(client1, looper):
    # These are dummy transactions, just to verify the client retrieval
    #  is working correctly
    h1 = "06b9a6eacd7a77b9361123fd19776455eb16b9c83426a1abbf514a414792b73f"
    h2 = "6f186f0b9303e2affde0b5d5e6586a633460a224b2a47f2a645cd5674185cf0b"
    h3 = "6f186f0b9303e2affde0b5d7f2a645cd5674185cf0b5e6586a633460a224b2a4"
    h4 = "6f4b6612125fb3a0daecd2799dfd6c9c299424fd920f9b308110a2c1fbd8f443"
    h5 = "6f4b6612125fba2c1fbd8f4433a0daecd2799dfd6c9c299424fd920f9b308110"
    operations = [{DATA: h1, TXN_TYPE: IDPROOF, TARGET_NYM: 'n/a'},
                  {DATA: h2, TXN_TYPE: IDPROOF, TARGET_NYM: 'n/a'},
                  {DATA: h3, TXN_TYPE: IDPROOF, TARGET_NYM: 'n/a'},
                  {ROLE: h4, TXN_TYPE: IDPROOF, TARGET_NYM: 'n/a'},
                  {ROLE: h5, TXN_TYPE: IDPROOF, TARGET_NYM: 'n/a'}]

    client1.submit(*operations)

    def chk():
        assert len(client1.getTxnsByAttribute(DATA)) == 3
        assert len(client1.getTxnsByAttribute(ROLE)) == 2

    looper.run(eventually(chk, retryWait=1, timeout=10))


def testNonSponsorCannotCreateAUser(genned, looper, nodeSet, tdir):
    sseed = b'this is a secret sponsor seed...'
    sponsorSigner = SimpleSigner('user', sseed)
    sponsor = genConnectedTestClient(looper, nodeSet, tmpdir=tdir,
                                     signer=sponsorSigner)

    useed = b'this is a secret apricot seed...'
    userSigner = SimpleSigner('user', useed)

    userNym = userSigner.verstr

    op = {
        ORIGIN: sponsorSigner.verstr,
        TARGET_NYM: userNym,
        TXN_TYPE: ADD_NYM,
        ROLE: USER
    }

    submitAndCheckNacks(looper, sponsor, op)


@pytest.fixture(scope="module")
def userSignerA(genned, sponsor, sponsorSigner, looper, addedSponsor):
    return addUser(looper, sponsor, sponsorSigner, 'userA')


@pytest.fixture(scope="module")
def userSignerB(genned, sponsor, sponsorSigner, looper, addedSponsor):
    return addUser(looper, sponsor, sponsorSigner, 'userB')


def testSponsorCreatesAUser(userSignerA):
    pass


@pytest.fixture(scope="module")
def attrib(userSignerA, sponsor, sponsorSigner, looper):

    data = {'name': 'Mario'}

    op = {
        ORIGIN: sponsorSigner.verstr,
        TARGET_NYM: userSignerA.verstr,
        TXN_TYPE: ADD_ATTR,
        DATA: data
    }

    submitAndCheck(looper, sponsor, op)


def testSponsorAddsAttributeForUser(attrib):
    pass


def testNonSponsorCannotAddAttributeForUser(userSignerA, looper, nodeSet, tdir):
    rand = SimpleSigner('random')
    randCli = clientFromSigner(rand, looper, nodeSet, tdir)
    
    data = {'name': 'Mario'}

    op = {
        ORIGIN: rand.verstr,
        TARGET_NYM: userSignerA.verstr,
        TXN_TYPE: ADD_ATTR,
        DATA: data
    }

    submitAndCheckNacks(looper, randCli, op)


def testOnlyUsersSponsorCanAddAttribute(userSignerA, looper, nodeSet, tdir,
                                        steward, stewardSigner, genned):
    newSponsorSigner = SimpleSigner('new sponsor')
    newSponsor = clientFromSigner(newSponsorSigner, looper, nodeSet, tdir)
    anotherSponsor(genned, steward, stewardSigner, looper, newSponsorSigner)

    data = {'name': 'Mario'}

    op = {
        ORIGIN: newSponsorSigner.verstr,
        TARGET_NYM: userSignerA.verstr,
        TXN_TYPE: ADD_ATTR,
        DATA: data
    }

    submitAndCheckNacks(looper, newSponsor, op)


def testStewardCannotAddUsersAttribute(userSignerA, looper, nodeSet, tdir,
                                        steward, stewardSigner, genned):
    data = {'name': 'Mario'}

    op = {
        ORIGIN: stewardSigner.verstr,
        TARGET_NYM: userSignerA.verstr,
        TXN_TYPE: ADD_ATTR,
        DATA: data
    }

    submitAndCheckNacks(looper, steward, op)


@pytest.mark.xfail()
def testSponsorAddedAttributeIsEncrypted(attrib):
    raise NotImplementedError


@pytest.mark.xfail()
def testSponsorAddedAttributeCanBeChanged(attrib):
    # TODO but only by user(if user has taken control of his identity) and
    # sponsor
    raise NotImplementedError
