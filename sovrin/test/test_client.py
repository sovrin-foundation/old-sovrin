import json
from contextlib import contextmanager

import base58
import libnacl.public
import pytest
from plenum.common.log import getlogger
from plenum.common.signer_simple import SimpleSigner
from plenum.common.txn import REQNACK, ENC, DATA, REPLY, TXN_TIME
from plenum.common.types import f, OP_FIELD_NAME
from plenum.common.util import adict
from plenum.common.eventually import eventually

from sovrin.client.client import Client
from sovrin.client.wallet.attribute import Attribute, LedgerStore
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.identity import Identity
from sovrin.common.txn import ATTRIB, NYM, TARGET_NYM, TXN_TYPE, ROLE, \
    SPONSOR, TXN_ID, NONCE, SKEY
from sovrin.common.util import getSymmetricallyEncryptedVal
from sovrin.test.helper import genTestClient, createNym, submitAndCheck, \
    makeAttribRequest, makeGetNymRequest, addAttributeAndCheck, TestNode

logger = getlogger()

whitelistArray = []


def whitelist():
    return whitelistArray


def checkNacks(client, reqId, contains='', nodeCount=4):
    logger.debug("looking for :{}".format(reqId))
    reqs = [x for x, _ in client.inBox if x[OP_FIELD_NAME] == REQNACK and
            x[f.REQ_ID.nm] == reqId]
    for r in reqs:
        logger.debug("printing r :{}".format(r))
        assert f.REASON.nm in r
        assert contains in r[f.REASON.nm]
    assert len(reqs) == nodeCount


# TODO Ordering of parameters is bad
def submitAndCheckNacks(looper, client, wallet, op, identifier,
                        contains='UnauthorizedClientRequest'):
    req = wallet.signOp(op, identifier=identifier)
    wallet.pendRequest(req)
    reqs = wallet.preparePending()
    client.submitReqs(*reqs)
    looper.run(eventually(checkNacks,
                          client,
                          req.reqId,
                          contains, retryWait=1, timeout=15))


@pytest.fixture(scope="module")
def attributeName():
    return 'name'


@pytest.fixture(scope="module")
def attributeValue():
    return 'Mario'


@pytest.fixture(scope="module")
def attributeData(attributeName, attributeValue):
    return json.dumps({attributeName: attributeValue})


@pytest.fixture(scope="module")
def addedRawAttribute(userWalletA: Wallet, sponsor: Client,
                      sponsorWallet: Wallet, attributeData, looper):
    attrib = Attribute(name='test attribute',
                       origin=sponsorWallet.defaultId,
                       value=attributeData,
                       dest=userWalletA.defaultId,
                       ledgerStore=LedgerStore.RAW)
    addAttributeAndCheck(looper, sponsor, sponsorWallet, attrib)
    return attrib


@pytest.fixture(scope="module")
def symEncData(attributeData):
    encData, secretKey = getSymmetricallyEncryptedVal(attributeData)
    return adict(data=attributeData, encData=encData, secretKey=secretKey)


@pytest.fixture(scope="module")
def addedEncryptedAttribute(userIdA, sponsor, sponsorWallet, looper,
                            symEncData):
    op = {
        TARGET_NYM: userIdA,
        TXN_TYPE: ATTRIB,
        ENC: symEncData.encData
    }

    return submitAndCheck(looper, sponsor, sponsorWallet, op)[0]


@pytest.fixture(scope="module")
def nonSponsor(looper, nodeSet, tdir):
    sseed = b'this is a secret sponsor seed...'
    signer = SimpleSigner(seed=sseed)
    c, _ = genTestClient(nodeSet, tmpdir=tdir, usePoolLedger=True)
    w = Wallet(c.name)
    w.addIdentifier(signer=signer)
    c.registerObserver(w.handleIncomingReply)
    looper.add(c)
    looper.run(c.ensureConnectedToNodes())
    return c, w


@pytest.fixture(scope="module")
def anotherSponsor(nodeSet, steward, stewardWallet, tdir, looper):
    sseed = b'this is 1 secret sponsor seed...'
    signer = SimpleSigner(seed=sseed)
    c, _ = genTestClient(nodeSet, tmpdir=tdir, usePoolLedger=True)
    w = Wallet(c.name)
    w.addIdentifier(signer=signer)
    c.registerObserver(w.handleIncomingReply)
    looper.add(c)
    looper.run(c.ensureConnectedToNodes())
    createNym(looper, signer.identifier, steward, stewardWallet,
              role=SPONSOR, verkey=signer.verkey)
    return c, w


def testCreateStewardWallet(stewardWallet):
    pass


@contextmanager
def whitelistextras(*msg):
    global whitelistArray
    ins = {m: (m in whitelistArray) for m in msg}
    [whitelistArray.append(m) for m, _in in ins.items() if not _in]
    yield
    [whitelistArray.remove(m) for m, _in in ins.items() if not _in]


def testNonStewardCannotCreateASponsor(nodeSet, client1, wallet1, looper):

    with whitelistextras("UnknownIdentifier"):
        seed = b'this is a secret sponsor seed...'
        sponsorSigner = SimpleSigner(seed=seed)

        sponsorNym = sponsorSigner.identifier

        op = {
            TARGET_NYM: sponsorNym,
            TXN_TYPE: NYM,
            ROLE: SPONSOR
        }

        submitAndCheckNacks(looper=looper, client=client1, wallet=wallet1, op=op,
                            identifier=wallet1.defaultId,
                            contains="UnknownIdentifier")


def testStewardCreatesASponsor(steward, addedSponsor):
    pass


@pytest.mark.skipif(True, reason="Cannot create another sponsor with same nym")
def testStewardCreatesAnotherSponsor(nodeSet, steward, stewardWallet, looper,
                                     sponsorWallet):
    createNym(looper, sponsorWallet.defaultId, steward, stewardWallet, SPONSOR)
    return sponsorWallet


def testNonSponsorCannotCreateAUser(nodeSet, looper, nonSponsor):
    with whitelistextras("UnknownIdentifier"):
        client, wallet = nonSponsor
        useed = b'this is a secret apricot seed...'
        userSigner = SimpleSigner(seed=useed)

        userNym = userSigner.identifier

        op = {
            TARGET_NYM: userNym,
            TXN_TYPE: NYM
        }

        submitAndCheckNacks(looper, client, wallet, op,
                            identifier=wallet.defaultId,
                            contains="UnknownIdentifier")


def testSponsorCreatesAUser(steward, userWalletA):
    pass


@pytest.fixture(scope="module")
def nymsAddedInQuickSuccession(nodeSet, addedSponsor, looper,
                               sponsor, sponsorWallet):
    usigner = SimpleSigner()
    nym = usigner.verkey
    idy = Identity(identifier=nym)
    sponsorWallet.addSponsoredIdentity(idy)
    # Creating a NYM request with same nym again
    req = idy.ledgerRequest()
    sponsorWallet._pending.appendleft((req, idy.identifier))
    reqs = sponsorWallet.preparePending()
    sponsor.submitReqs(*reqs)

    def check():
         assert sponsorWallet._sponsored[nym].seqNo

    looper.run(eventually(check, timeout=2))

    looper.run(eventually(checkNacks,
                          sponsor,
                          req.reqId,
                          "is already added",
                          retryWait=1, timeout=15))
    count = 0
    for node in nodeSet:
        txns = node.domainLedger.getAllTxn()
        for seq, txn in txns.items():
            if txn[TXN_TYPE] == NYM and txn[TARGET_NYM] == usigner.identifier:
                count += 1

    assert(count == len(nodeSet))


@pytest.mark.skipif(True, reason="NYM transaction now used to update too")
def testAddNymsInQuickSuccession(nymsAddedInQuickSuccession):
    pass


def testSponsorAddsAttributeForUser(addedRawAttribute):
    pass


def testClientGetsResponseWithoutConsensusForUsedReqId(nodeSet, looper, steward,
                                                       addedSponsor, sponsor,
                                                       userWalletA,
                                                       attributeName,
                                                       attributeData,
                                                       addedRawAttribute):
    lastReqId = None
    replies = {}
    for msg, sender in reversed(sponsor.inBox):
        if msg[OP_FIELD_NAME] == REPLY:
            if not lastReqId:
                lastReqId = msg[f.RESULT.nm][f.REQ_ID.nm]
            if msg.get(f.RESULT.nm, {}).get(f.REQ_ID.nm) == lastReqId:
                replies[sender] = msg
            if len(replies) == len(nodeSet):
                break

    sponsorWallet = addedSponsor
    attrib = Attribute(name=attributeName,
                       origin=sponsorWallet.defaultId,
                       value=attributeData,
                       dest=userWalletA.defaultId,
                       ledgerStore=LedgerStore.RAW)
    sponsorWallet.addAttribute(attrib)
    req = sponsorWallet.preparePending()[0]
    _, key = sponsorWallet._prepared.pop((req.identifier, req.reqId))
    req.reqId = lastReqId
    req.signature = sponsorWallet.signMsg(msg=req.getSigningState(),
                                          identifier=req.identifier)
    sponsorWallet._prepared[req.identifier, req.reqId] = req, key
    sponsor.submitReqs(req)

    def chk():
        nonlocal sponsor, lastReqId, replies
        for node in nodeSet:
            last = node.spylog.getLast(TestNode.getReplyFor.__name__)
            assert last
            result = last.result
            assert result is not None

            # TODO: Time is not equal as some precision is lost while storing
            # in oientdb, using seconds may be an option, need to think of a
            # use cases where time in milliseconds is required
            replies[node.clientstack.name][f.RESULT.nm].pop(TXN_TIME, None)
            result.result.pop(TXN_TIME, None)

            assert replies[node.clientstack.name][f.RESULT.nm] == result.result

    looper.run(eventually(chk, retryWait=1, timeout=5))


def checkGetAttr(reqKey, sponsor, attrName, attrValue):
    reply, status = sponsor.getReply(*reqKey)
    assert reply
    data = json.loads(reply.get(DATA))
    assert status == "CONFIRMED" and \
           (data is not None and data.get(attrName) == attrValue)


def getAttribute(looper, sponsor, sponsorWallet, userIdA, attributeName,
                 attributeValue):
    attrib = Attribute(name=attributeName,
                       value=None,
                       dest=userIdA,
                       ledgerStore=LedgerStore.RAW)
    req = sponsorWallet.requestAttribute(attrib,
                                         sender=sponsorWallet.defaultId)
    sponsor.submitReqs(req)
    looper.run(eventually(checkGetAttr, req.key, sponsor,
                          attributeName, attributeValue, retryWait=1,
                          timeout=20))


@pytest.fixture(scope="module")
def checkAddAttribute(userWalletA, sponsor, sponsorWallet, attributeName,
                      attributeValue, addedRawAttribute, looper):
    getAttribute(looper=looper,
                 sponsor=sponsor,
                 sponsorWallet=sponsorWallet,
                 userIdA=userWalletA.defaultId,
                 attributeName=attributeName,
                 attributeValue=attributeValue)


def testSponsorGetAttrsForUser(checkAddAttribute):
    pass


def testNonSponsorCannotAddAttributeForUser(nodeSet, nonSponsor, userIdA,
                                            looper, attributeData):
    with whitelistextras("UnknownIdentifier"):
        client, wallet = nonSponsor
        attrib = Attribute(name='test1 attribute',
                           origin=wallet.defaultId,
                           value=attributeData,
                           dest=userIdA,
                           ledgerStore=LedgerStore.RAW)
        reqs = makeAttribRequest(client, wallet, attrib)
        looper.run(eventually(checkNacks,
                              client,
                              reqs[0].reqId,
                              "UnknownIdentifier", retryWait=1, timeout=15))


def testOnlyUsersSponsorCanAddAttribute(nodeSet, looper,
                                        steward, stewardWallet,
                                        attributeData, anotherSponsor, userIdA):
    with whitelistextras("UnauthorizedClientRequest"):
        client, wallet = anotherSponsor
        attrib = Attribute(name='test2 attribute',
                           origin=wallet.defaultId,
                           value=attributeData,
                           dest=userIdA,
                           ledgerStore=LedgerStore.RAW)
        reqs = makeAttribRequest(client, wallet, attrib)
        looper.run(eventually(checkNacks,
                              client,
                              reqs[0].reqId,
                              retryWait=1, timeout=15))


def testStewardCannotAddUsersAttribute(nodeSet, looper, steward,
                                       stewardWallet, userIdA, attributeData):
    with whitelistextras("UnauthorizedClientRequest"):
        attrib = Attribute(name='test3 attribute',
                           origin=stewardWallet.defaultId,
                           value=attributeData,
                           dest=userIdA,
                           ledgerStore=LedgerStore.RAW)
        reqs = makeAttribRequest(steward, stewardWallet, attrib)
        looper.run(eventually(checkNacks,
                              steward,
                              reqs[0].reqId,
                              retryWait=1, timeout=15))


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
        TARGET_NYM: userSignerA.verstr,
        TXN_TYPE: ATTRIB,
        NONCE: base58.b58encode(nonce),
        ENC: base58.b58encode(boxedMsg)
    }
    submitAndCheck(looper, sponsor, op,
                   identifier=sponsorSigner.verstr)


@pytest.mark.skipif(True, reason="Pending implementation")
def testSponsorAddedAttributeCanBeChanged(addedRawAttribute):
    # TODO but only by user(if user has taken control of his identity) and
    # sponsor
    raise NotImplementedError


def testGetAttribute(nodeSet, addedSponsor, sponsorWallet: Wallet, sponsor,
                     userIdA, addedRawAttribute, attributeData):
    assert attributeData in [a.value for a in sponsorWallet.getAttributesForNym(userIdA)]


# TODO: Ask Jason, if getting the latest attribute makes sense since in case
# of encrypted and hashed attributes, there is no name.
def testLatestAttrIsReceived(nodeSet, addedSponsor, sponsorWallet, looper,
                             sponsor, userIdA):

    attr1 = json.dumps({'name': 'Mario'})
    attrib = Attribute(name='name',
                       origin=sponsorWallet.defaultId,
                       value=attr1,
                       dest=userIdA,
                       ledgerStore=LedgerStore.RAW)
    addAttributeAndCheck(looper, sponsor, sponsorWallet, attrib)
    assert attr1 in [a.value for a in sponsorWallet.getAttributesForNym(userIdA)]

    attr2 = json.dumps({'name': 'Luigi'})
    attrib = Attribute(name='name',
                       origin=sponsorWallet.defaultId,
                       value=attr2,
                       dest=userIdA,
                       ledgerStore=LedgerStore.RAW)
    addAttributeAndCheck(looper, sponsor, sponsorWallet, attrib)
    logger.debug([a.value for a in sponsorWallet.getAttributesForNym(userIdA)])
    assert attr2 in [a.value for a in
                     sponsorWallet.getAttributesForNym(userIdA)]


@pytest.mark.skipif(True, reason="Test not implemented")
def testGetTxnsNoSeqNo():
    """
    Test GET_TXNS from client and do not provide any seqNo to fetch from
    """
    pass


@pytest.mark.skipif(True, reason="Come back to it later since "
                                 "requestPendingTxns move to wallet")
def testGetTxnsSeqNo(nodeSet, addedSponsor, tdir, sponsorWallet, looper):
    """
    Test GET_TXNS from client and provide seqNo to fetch from
    """
    sponsor = genTestClient(nodeSet, tmpdir=tdir, usePoolLedger=True)

    looper.add(sponsor)
    looper.run(sponsor.ensureConnectedToNodes())

    def chk():
        assert sponsor.spylog.count(sponsor.requestPendingTxns.__name__) > 0

    looper.run(eventually(chk, retryWait=1, timeout=3))


def testNonSponsoredNymCanDoGetNym(nodeSet, addedSponsor,
                                   sponsorWallet, tdir, looper):
    signer = SimpleSigner()
    someClient, _ = genTestClient(nodeSet, tmpdir=tdir, usePoolLedger=True)
    wallet = Wallet(someClient.name)
    wallet.addIdentifier(signer=signer)
    someClient.registerObserver(wallet.handleIncomingReply)
    looper.add(someClient)
    looper.run(someClient.ensureConnectedToNodes())
    needle = sponsorWallet.defaultId
    makeGetNymRequest(someClient, wallet, needle)
    looper.run(eventually(someClient.hasNym, needle, retryWait=1, timeout=5))


def testUserAddAttrsForHerSelf(nodeSet, looper, userClientA, userWalletA,
                               userIdA, attributeData):
    attr1 = json.dumps({'age': 25})
    attrib = Attribute(name='test4 attribute',
                       origin=userIdA,
                       value=attr1,
                       dest=userIdA,
                       ledgerStore=LedgerStore.RAW)
    addAttributeAndCheck(looper, userClientA, userWalletA, attrib)
