import json

import base58
import libnacl.public
import pytest

from plenum.client.signer import SimpleSigner
from plenum.common.request_types import f, OP_FIELD_NAME
from plenum.common.util import adict
from plenum.test.eventually import eventually
from sovrin.common.txn import ADD_ATTR, ADD_NYM, storedTxn, \
    STEWARD, TARGET_NYM, TXN_TYPE, ROLE, SPONSOR, ORIGIN, DATA, USER, IDPROOF, \
    TXN_ID, NONCE, SKEY, REFERENCE, newTxn, AddNym
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
        assert r[OP_FIELD_NAME] == 'REQNACK'
        assert f.REASON.nm in r
        assert contains in r[f.REASON.nm]
    assert len(reqs) == nodeCount


def submitAndCheck(looper, client, *op, identifier):
    txnsBefore = client.findTxns(TXN_TYPE)

    client.submit(*op, identifier=identifier)

    txnsAfter = []

    def checkTxnCountAdvanced():
        txnsAfter.extend(client.findTxns(TXN_TYPE))
        assert len(txnsAfter) > len(txnsBefore)

    looper.run(eventually(checkTxnCountAdvanced, retryWait=1, timeout=15))
    txnIdsBefore = [txn[TXN_ID] for txn in txnsBefore]
    return [txn for txn in txnsAfter if txn[TXN_ID] not in txnIdsBefore]


# TODO Ordering of parameters is bad
def submitAndCheckNacks(looper, client, op, identifier,
                        contains='UnauthorizedClientRequest'):
    client.submit(op, identifier=identifier)
    looper.run(eventually(checkNacks,
                          client,
                          client.lastReqId,
                          contains))


def createNym(looper, targetSigner, creatorClient, creatorSigner, role):
    nym = targetSigner.verstr
    op = {
        ORIGIN: creatorSigner.verstr,
        TARGET_NYM: nym,
        TXN_TYPE: ADD_NYM,
        ROLE: role
    }
    return submitAndCheck(looper, creatorClient, op,
                          identifier=creatorSigner.identifier)[0]


def addUser(looper, creatorClient, creatorSigner, name):
    usigner = SimpleSigner()
    createNym(looper, usigner, creatorClient, creatorSigner, USER)
    return usigner


@pytest.fixture(scope="module")
def addedSponsor(genned, steward, stewardSigner, looper, sponsorSigner):
    createNym(looper, sponsorSigner, steward, stewardSigner, SPONSOR)
    return sponsorSigner


@pytest.fixture(scope="module")
def anotherSponsor(genned, steward, stewardSigner, looper, sponsorSigner):
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
                        identifier=stewardSigner.identifier,
                        contains="InvalidIdentifier")


def testStewardCreatesASponsor(addedSponsor):
    pass


@pytest.mark.xfail(reason="Cannot create another sponsor with same nym")
def testStewardCreatesAnotherSponsor(genned, steward, stewardSigner, looper,
                                     nodeSet, tdir, sponsorSigner):
    createNym(looper, sponsorSigner, steward, stewardSigner, SPONSOR)
    return sponsorSigner


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

    submitAndCheckNacks(looper, sponsor, op, identifier=sponsNym,
                        contains="InvalidIdentifier")


def testSponsorCreatesAUser(userSignerA):
    pass


def testSponsorAddsAttributeForUser(addedAttribute):
    pass


def testSponsorAddsAliasForUser(addedSponsor, looper, sponsor, sponsorSigner):
    userSigner = SimpleSigner()
    txn = createNym(looper, userSigner, sponsor, sponsorSigner, USER)

    sponsNym = sponsorSigner.verstr

    op = {
        ORIGIN: sponsNym,
        TARGET_NYM: "jasonlaw",
        TXN_TYPE: ADD_NYM,
        # TODO: Should REFERENCE be symmetrically encrypted and the key
        # should then be disclosed in another transaction
        REFERENCE: txn[TXN_ID],
        ROLE: USER
    }

    submitAndCheck(looper, sponsor, op, identifier=sponsNym)


def testNonSponsorCannotAddAttributeForUser(userSignerA, looper, nodeSet, tdir,
                                            attributeData):
    seed = b'this is a not an apricot seed...'
    rand = SimpleSigner(seed=seed)
    randCli = clientFromSigner(rand, looper, nodeSet, tdir)

    nym = rand.verstr

    op = {
        ORIGIN: nym,
        TARGET_NYM: userSignerA.verstr,
        TXN_TYPE: ADD_ATTR,
        DATA: attributeData
    }

    submitAndCheckNacks(looper, randCli, op, identifier=nym,
                        contains="InvalidIdentifier")


def testOnlyUsersSponsorCanAddAttribute(userSignerA, looper, nodeSet, tdir,
                                        steward, stewardSigner, genned,
                                        attributeData):
    newSponsorSigner = SimpleSigner()
    newSponsor = clientFromSigner(newSponsorSigner, looper, nodeSet, tdir)
    anotherSponsor(genned, steward, stewardSigner, looper, newSponsorSigner)

    op = {
        ORIGIN: newSponsorSigner.verstr,
        TARGET_NYM: userSignerA.verstr,
        TXN_TYPE: ADD_ATTR,
        DATA: attributeData
    }

    submitAndCheckNacks(looper, newSponsor, op,
                        identifier=newSponsorSigner.verstr)


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


@pytest.mark.xfail(reason="Attribute encryption is done in client")
def testSponsorAddedAttributeIsEncrypted(addedEncryptedAttribute):
    pass


@pytest.mark.xfail()
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


@pytest.mark.xfail()
def testSponsorAddedAttributeCanBeChanged(addedAttribute):
    # TODO but only by user(if user has taken control of his identity) and
    # sponsor
    raise NotImplementedError


def testForGettingAttribute(sponsor, userSignerA, addedAttribute):
    assert sponsor.getAllAttributesForNym(userSignerA.verstr) == \
           [{'name': 'Mario'}]


def testLatestAttrIsReceived(looper, sponsor, sponsorSigner, userSignerA):
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