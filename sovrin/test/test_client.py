import json

import base58
import libnacl.public
import pytest

from plenum.client.signer import SimpleSigner
from plenum.common.txn import REQNACK
from plenum.common.types import f, OP_FIELD_NAME
from plenum.common.util import adict, getlogger
from plenum.test.eventually import eventually
from sovrin.common.txn import ADD_ATTR, ADD_NYM, \
    TARGET_NYM, TXN_TYPE, ROLE, SPONSOR, ORIGIN, DATA, USER, \
    TXN_ID, NONCE, SKEY, REFERENCE
from sovrin.common.util import getSymmetricallyEncryptedVal
from sovrin.test.helper import genConnectedTestClient, \
    clientFromSigner, genTestClient, createNym, submitAndCheck


logger = getlogger()


# TODO use wallet instead of SimpleSigner in client


def checkNacks(client, reqId, contains='', nodeCount=4):
    reqs = [x for x, _ in client.inBox if x[OP_FIELD_NAME] == REQNACK and
            x[f.REQ_ID.nm] == reqId]
    for r in reqs:
        assert f.REASON.nm in r
        assert contains in r[f.REASON.nm]
    assert len(reqs) == nodeCount


# TODO Ordering of parameters is bad
def submitAndCheckNacks(looper, client, op, identifier,
                        contains='UnauthorizedClientRequest'):
    client.submit(op, identifier=identifier)
    looper.run(eventually(checkNacks,
                          client,
                          client.lastReqId,
                          contains, retryWait=1, timeout=15))


def addUser(looper, creatorClient, creatorSigner, name):
    usigner = SimpleSigner()
    createNym(looper, usigner, creatorClient, creatorSigner, USER)
    return usigner


@pytest.fixture(scope="module")
def updatedSteward(steward):
    steward.requestPendingTxns()


@pytest.fixture(scope="module")
def addedSponsor(genned, steward, stewardSigner, looper, sponsorSigner):
    createNym(looper, sponsorSigner, steward, stewardSigner, SPONSOR)
    return sponsorSigner


@pytest.fixture(scope="module")
def userSignerA(genned, sponsor, sponsorSigner, looper, addedSponsor):
    return addUser(looper, sponsor, sponsorSigner, 'userA')


@pytest.fixture(scope="module")
def userSignerB(genned, sponsor, sponsorSigner, looper, addedSponsor):
    return addUser(looper, sponsor, sponsorSigner, 'userB')


@pytest.fixture(scope="module")
def attributeData():
    return json.dumps({'name': 'Mario'})


@pytest.fixture(scope="module")
def addedAttribute(userSignerA, sponsor, sponsorSigner, attributeData, looper):
    op = {
        ORIGIN: sponsorSigner.verstr,
        TARGET_NYM: userSignerA.verstr,
        TXN_TYPE: ADD_ATTR,
        DATA: attributeData
    }

    submitAndCheck(looper, sponsor, op, identifier=sponsorSigner.verstr)


@pytest.fixture(scope="module")
def symEncData(attributeData):
    encData, secretKey = getSymmetricallyEncryptedVal(attributeData)
    return adict(data=attributeData, encData=encData, secretKey=secretKey)


@pytest.fixture(scope="module")
def addedEncryptedAttribute(userSignerA, sponsor, sponsorSigner, looper,
                            symEncData):
    sponsorNym = sponsorSigner.verstr
    op = {
        ORIGIN: sponsorNym,
        TARGET_NYM: userSignerA.verstr,
        TXN_TYPE: ADD_ATTR,
        DATA: symEncData.encData
    }

    return submitAndCheck(looper, sponsor, op, identifier=sponsorNym)[0]


@pytest.fixture(scope="module")
def nonSponsor(looper, nodeSet, tdir):
    sseed = b'this is a secret sponsor seed...'
    sponsorSigner = SimpleSigner(seed=sseed)
    c = genTestClient(nodeSet, tmpdir=tdir, signer=sponsorSigner)
    for node in nodeSet:
        node.whitelistClient(c.name)
    looper.add(c)
    looper.run(c.ensureConnectedToNodes())
    return c


@pytest.fixture(scope="module")
def anotherSponsor(genned, steward, stewardSigner, tdir, looper, nodeSet):
    sseed = b'this is 1 secret sponsor seed...'
    signer = SimpleSigner(seed=sseed)
    c = genTestClient(nodeSet, tmpdir=tdir, signer=signer)
    for node in nodeSet:
        node.whitelistClient(c.name)
    looper.add(c)
    looper.run(c.ensureConnectedToNodes())
    createNym(looper, signer, steward, stewardSigner, SPONSOR)
    return c


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

    submitAndCheckNacks(looper=looper, client=steward, op=op,
                        identifier=stewardSigner.identifier,
                        contains="InvalidIdentifier")


def testStewardCreatesASponsor(updatedSteward, addedSponsor):
    pass


@pytest.mark.skipif(True, reason="Cannot create another sponsor with same nym")
def testStewardCreatesAnotherSponsor(genned, steward, stewardSigner, looper,
                                     nodeSet, tdir, sponsorSigner):
    createNym(looper, sponsorSigner, steward, stewardSigner, SPONSOR)
    return sponsorSigner


def testNonSponsorCannotCreateAUser(genned, looper, nodeSet, tdir, nonSponsor):

    sponsNym = nonSponsor.getSigner().verstr

    useed = b'this is a secret apricot seed...'
    userSigner = SimpleSigner(seed=useed)

    userNym = userSigner.verstr

    op = {
        ORIGIN: sponsNym,
        TARGET_NYM: userNym,
        TXN_TYPE: ADD_NYM,
        ROLE: USER
    }

    submitAndCheckNacks(looper, nonSponsor, op, identifier=sponsNym,
                        contains="InvalidIdentifier")


def testSponsorCreatesAUser(userSignerA):
    pass


def testSponsorAddsAttributeForUser(addedAttribute):
    pass


def testSponsorAddsAliasForUser(addedSponsor, looper, sponsor, sponsorSigner):
    userSigner = SimpleSigner()
    txnId = createNym(looper, userSigner, sponsor, sponsorSigner, USER)

    sponsNym = sponsorSigner.verstr

    op = {
        ORIGIN: sponsNym,
        TARGET_NYM: "jasonlaw",
        TXN_TYPE: ADD_NYM,
        # TODO: Should REFERENCE be symmetrically encrypted and the key
        # should then be disclosed in another transaction
        REFERENCE: txnId,
        ROLE: USER
    }

    submitAndCheck(looper, sponsor, op, identifier=sponsNym)


def testNonSponsorCannotAddAttributeForUser(nonSponsor, userSignerA, looper, nodeSet, tdir,
                                            attributeData):

    nym = nonSponsor.getSigner().verstr

    op = {
        ORIGIN: nym,
        TARGET_NYM: userSignerA.verstr,
        TXN_TYPE: ADD_ATTR,
        DATA: attributeData
    }

    submitAndCheckNacks(looper, nonSponsor, op, identifier=nym,
                        contains="InvalidIdentifier")


def testOnlyUsersSponsorCanAddAttribute(userSignerA, looper, nodeSet, tdir,
                                        steward, stewardSigner, genned,
                                        attributeData, anotherSponsor):
    op = {
        ORIGIN: anotherSponsor.getSigner().verstr,
        TARGET_NYM: userSignerA.verstr,
        TXN_TYPE: ADD_ATTR,
        DATA: attributeData
    }

    submitAndCheckNacks(looper, anotherSponsor, op,

                        identifier=anotherSponsor.getSigner().verstr)


def testStewardCannotAddUsersAttribute(userSignerA, looper, nodeSet, tdir,
                                       steward, stewardSigner, genned,
                                       attributeData):
    op = {
        ORIGIN: stewardSigner.verstr,
        TARGET_NYM: userSignerA.verstr,
        TXN_TYPE: ADD_ATTR,
        DATA: attributeData
    }

    submitAndCheckNacks(looper, steward, op,
                        identifier=stewardSigner.verstr)


@pytest.mark.skipif(True, reason="Attribute encryption is done in client")
def testSponsorAddedAttributeIsEncrypted(addedEncryptedAttribute):
    pass


@pytest.mark.skipif(True, reason="Attribute Disclosure is not done for now")
def testSponsorDisclosesEncryptedAttribute(addedEncryptedAttribute, symEncData,
                                           looper, userSignerA, sponsorSigner,
                                           sponsor):
    box = libnacl.public.Box(sponsorSigner.naclSigner.keyraw,
                             userSignerA.naclSigner.verraw)

    data = json.dumps({SKEY: symEncData.secretKey,
                       TXN_ID: addedEncryptedAttribute[TXN_ID]})
    nonce, boxedMsg = box.encrypt(data.encode(), pack_nonce=False)

    op = {
        ORIGIN: sponsorSigner.verstr,
        TARGET_NYM: userSignerA.verstr,
        TXN_TYPE: ADD_ATTR,
        NONCE: base58.b58encode(nonce),
        DATA: base58.b58encode(boxedMsg)
    }
    submitAndCheck(looper, sponsor, op,
                   identifier=sponsorSigner.verstr)


@pytest.mark.skipif(True, reason="Pending implementation")
def testSponsorAddedAttributeCanBeChanged(addedAttribute):
    # TODO but only by user(if user has taken control of his identity) and
    # sponsor
    raise NotImplementedError


def testGetAttribute(sponsor, userSignerA, addedAttribute):
    assert sponsor.getAllAttributesForNym(userSignerA.verstr) == \
           [{'name': 'Mario'}]


def testLatestAttrIsReceived(looper, genned, sponsor, sponsorSigner, userSignerA):
    attr1 = json.dumps({'name': 'Mario'})
    op = {
        ORIGIN: sponsorSigner.verstr,
        TARGET_NYM: userSignerA.verstr,
        TXN_TYPE: ADD_ATTR,
        DATA: attr1
    }
    submitAndCheck(looper, sponsor, op, identifier=sponsorSigner.verstr)
    assert sponsor.getAllAttributesForNym(userSignerA.verstr) == \
           [{'name': 'Mario'}]

    attr2 = json.dumps({'name': 'Tom'})
    op = {
        ORIGIN: sponsorSigner.verstr,
        TARGET_NYM: userSignerA.verstr,
        TXN_TYPE: ADD_ATTR,
        DATA: attr2
    }
    submitAndCheck(looper, sponsor, op, identifier=sponsorSigner.verstr)
    assert sponsor.getAllAttributesForNym(userSignerA.verstr) == \
           [{'name': 'Tom'}]
