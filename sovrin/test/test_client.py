import json

import base58
import libnacl.public
import pytest

from plenum.client.signer import SimpleSigner
from plenum.common.request_types import f
from plenum.test.eventually import eventually
from plenum.test.testing_utils import adict
from sovrin.common.txn import ADD_ATTR, ADD_NYM, storedTxn, \
    STEWARD, TARGET_NYM, TXN_TYPE, ROLE, SPONSOR, ORIGIN, DATA, USER, IDPROOF, \
    TXN_ID, NONCE, SKEY, newTxn, AddNym
from sovrin.common.util import getSymmetricallyEncryptedVal
from sovrin.test.helper import genConnectedTestClient, \
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


def submitAndCheck(looper, client, op, identifier):
    txnsBefore = client.getTxnsByAttribute(TXN_TYPE)

    client.submit(op, identifier=identifier)

    txnsAfter = []

    def checkTxnCountAdvanced():
        txnsAfter.extend(client.getTxnsByAttribute(TXN_TYPE))
        assert len(txnsAfter) > len(txnsBefore)

    looper.run(eventually(checkTxnCountAdvanced, retryWait=1, timeout=15))
    txnIdsBefore = [txn[TXN_ID] for txn in txnsBefore]
    return [txn for txn in txnsAfter if txn[TXN_ID] not in txnIdsBefore]


def submitAndCheckNacks(looper, client, op, identifier,
                        contains='UnauthorizedClientRequest'):
    client.submit(op, identifier=identifier)
    looper.run(eventually(checkNacks,
                          client,
                          client.lastReqId,
                          contains))


def createNym(looper, targetSigner, creatorClient, creatorSigner, role):
    nym = targetSigner.verstr
    op = AddNym(origin=creatorSigner.verstr,
                target=nym,
                role=role)
    submitAndCheck(looper, creatorClient, op, creatorSigner.identifier)
    return targetSigner


def addUser(looper, creatorClient, creatorSigner, name):
    usigner = SimpleSigner()
    return createNym(looper, usigner, creatorClient, creatorSigner, USER)


@pytest.fixture(scope="module")
def addedSponsor(genned, steward, stewardSigner, looper, sponsorSigner):
    return createNym(looper, sponsorSigner, steward, stewardSigner, SPONSOR)


@pytest.fixture(scope="module")
def anotherSponsor(genned, steward, stewardSigner, looper, sponsorSigner):
    return createNym(looper, sponsorSigner, steward, stewardSigner, SPONSOR)


@pytest.fixture(scope="module")
def userSignerA(genned, sponsor, sponsorSigner, looper, addedSponsor):
    return addUser(looper, sponsor, sponsorSigner, 'userA')


@pytest.fixture(scope="module")
def userSignerB(genned, sponsor, sponsorSigner, looper, addedSponsor):
    return addUser(looper, sponsor, sponsorSigner, 'userB')


@pytest.fixture(scope="module")
def attrib(userSignerA, sponsor, sponsorSigner, looper):

    data = {'name': 'Mario'}

    op = {
        ORIGIN: sponsorSigner.verstr,
        TARGET_NYM: userSignerA.verstr,
        TXN_TYPE: ADD_ATTR,
        DATA: data
    }

    submitAndCheck(looper, sponsor, op, sponsorSigner.verstr)


@pytest.fixture(scope="module")
def encryptedAttrib(userSignerA, sponsor, sponsorSigner, looper, symEncData):

    op = {
        ORIGIN: sponsorSigner.verstr,
        TARGET_NYM: userSignerA.verstr,
        TXN_TYPE: ADD_ATTR,
        DATA: symEncData.data
    }

    return submitAndCheck(looper, sponsor, op, sponsorSigner.verstr)


@pytest.fixture(scope="module")
def symEncData():
    data = json.dumps({'name': 'Mario'})
    encVal, secretKey = getSymmetricallyEncryptedVal(data)
    return adict(data=data, encVal=encVal, secretKey=secretKey)


def testNonStewardCannotCreateASponsor(steward, stewardSigner, looper, nodeSet):
    seed = b'this is a secret sponsor seed...'
    sponsorSigner = SimpleSigner(seed)

    sponsorNym = sponsorSigner.verstr

    op = {
        ORIGIN: stewardSigner.verstr,
        TARGET_NYM: sponsorNym,
        TXN_TYPE: ADD_NYM,
        ROLE: SPONSOR
    }

    for node in nodeSet:
        node.whitelistClient(steward.name)
    submitAndCheckNacks(looper=looper, client=steward, op=op,
                        identifier=stewardSigner.identifier, contains="InvalidIdentifier")


def testStewardCreatesASponsor(addedSponsor):
    pass


def testStewardCreatesAnotherSponsor(genned, steward, stewardSigner, looper,
                               nodeSet, tdir, sponsorSigner):
    return createNym(looper, sponsorSigner, steward, stewardSigner, SPONSOR)


def testNonSponsorCannotCreateAUser(genned, looper, nodeSet, tdir):
    sseed = b'this is a secret sponsor seed...'
    sponsorSigner = SimpleSigner(seed=sseed)
    sponsor = genConnectedTestClient(looper, nodeSet, tmpdir=tdir,
                                     signer=sponsorSigner)

    sponsNym = sponsorSigner.verstr

    useed = b'this is a secret apricot seed...'
    userSigner = SimpleSigner(seed=useed)

    userNym = userSigner.verstr

    op = {
        ORIGIN: sponsNym,
        TARGET_NYM: userNym,
        TXN_TYPE: ADD_NYM,
        ROLE: USER
    }

    submitAndCheckNacks(looper, sponsor, op, sponsNym, contains="InvalidIdentifier")


def testSponsorCreatesAUser(userSignerA):
    pass


def testSponsorAddsAttributeForUser(attrib):
    pass


def testNonSponsorCannotAddAttributeForUser(userSignerA, looper, nodeSet, tdir):
    seed = b'this is a not an apricot seed...'
    rand = SimpleSigner(seed=seed)
    randCli = clientFromSigner(rand, looper, nodeSet, tdir)

    nym = rand.verstr

    data = {'name': 'Mario'}

    op = {
        ORIGIN: nym,
        TARGET_NYM: userSignerA.verstr,
        TXN_TYPE: ADD_ATTR,
        DATA: data
    }

    submitAndCheckNacks(looper, randCli, op, nym, contains="InvalidIdentifier")


def testOnlyUsersSponsorCanAddAttribute(userSignerA, looper, nodeSet, tdir,
                                        steward, stewardSigner, genned):
    newSponsorSigner = SimpleSigner()
    newSponsor = clientFromSigner(newSponsorSigner, looper, nodeSet, tdir)
    anotherSponsor(genned, steward, stewardSigner, looper, newSponsorSigner)

    data = {'name': 'Mario'}

    op = {
        ORIGIN: newSponsorSigner.verstr,
        TARGET_NYM: userSignerA.verstr,
        TXN_TYPE: ADD_ATTR,
        DATA: data
    }

    submitAndCheckNacks(looper, newSponsor, op, newSponsorSigner.verstr)


def testStewardCannotAddUsersAttribute(userSignerA, looper, nodeSet, tdir,
                                        steward, stewardSigner, genned):
    data = {'name': 'Mario'}

    op = {
        ORIGIN: stewardSigner.verstr,
        TARGET_NYM: userSignerA.verstr,
        TXN_TYPE: ADD_ATTR,
        DATA: data
    }

    submitAndCheckNacks(looper, steward, op, stewardSigner.verstr)


def testSponsorAddedAttributeIsEncrypted(encryptedAttrib):
    pass


def testSponsorDisclosesEncryptedAttribute(encryptedAttrib, symEncData, looper,
                                           userSignerA, sponsorSigner, sponsor):
    box = libnacl.public.Box(sponsorSigner.naclSigner.keyraw,
                             userSignerA.naclSigner.verraw)

    data = json.dumps({SKEY: symEncData.secretKey, TXN_ID: encryptedAttrib[
        0][TXN_ID]})
    nonce, boxedMsg = box.encrypt(data.encode(), pack_nonce=False)

    op = {
        ORIGIN: sponsorSigner.verstr,
        TARGET_NYM: userSignerA.verstr,
        TXN_TYPE: ADD_ATTR,
        NONCE: base58.b58encode(nonce),
        DATA: base58.b58encode(boxedMsg)
    }
    submitAndCheck(looper, sponsor, op, sponsorSigner.verstr)


@pytest.mark.xfail()
def testSponsorAddedAttributeCanBeChanged(attrib):
    # TODO but only by user(if user has taken control of his identity) and
    # sponsor
    raise NotImplementedError