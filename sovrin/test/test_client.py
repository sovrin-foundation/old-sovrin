import pytest
from plenum.client.signer import SimpleSigner
from plenum.test.eventually import eventually

from sovrin.common.txn import ADD_ATTR, ADD_NYM, storedTxn, \
    STEWARD, TARGET_NYM, TXN_TYPE, ROLE, SPONSOR, ORIGIN, DATA


@pytest.fixture(scope="module")
def genesisTxns(stewardSigner):
    nym = stewardSigner.verstr
    return [storedTxn(ADD_NYM, nym,
                "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b",
                role=STEWARD),
        ]


# TODO use wallet instead of SimpleSigner in client


def testNonStewardCannotCreateASponsor(steward, stewardSigner, looper,
                                       nodeSet, tdir):
    seed = b'this is a secret sponsor seed...'
    sponsorSigner = SimpleSigner('sponsor', seed)

    sponsorNym = sponsorSigner.verstr

    op = {
        ORIGIN: stewardSigner.verstr,
        TARGET_NYM: sponsorNym,
        TXN_TYPE: ADD_NYM,
        ROLE: SPONSOR
    }

    txnCount = len(steward.getTxnsByAttribute(TXN_TYPE))

    # TODO Should submit add ORIGIN on its own
    steward.submit(op)
    # looper.runFor(5)

    def chk():
        with pytest.raises(AssertionError):
            assert len(steward.getTxnsByAttribute(TXN_TYPE)) != txnCount

    looper.run(eventually(chk, retryWait=1, timeout=10))


def testStewardCreatesASponsor(genned, steward, stewardSigner, looper,
                               nodeSet, tdir):
    seed = b'this is a secret sponsor seed...'
    sponsorSigner = SimpleSigner('sponsor', seed)

    sponsorNym = sponsorSigner.verstr

    op = {
        ORIGIN: stewardSigner.verstr,
        TARGET_NYM: sponsorNym,
        TXN_TYPE: ADD_NYM,
        ROLE: SPONSOR
    }

    txnCount = len(steward.getTxnsByAttribute(TXN_TYPE))

    # TODO Should submit add ORIGIN on its own to operation?
    steward.submit(op)

    def chk():
        assert len(steward.getTxnsByAttribute(TXN_TYPE)) == txnCount + 1

    looper.run(eventually(chk, retryWait=1, timeout=15))


    #
    # s = genTestClient(nodeSet, signer=sponsorSigner, tmpdir=tdir)
    # looper.add(s)
    # looper.run(s.ensureConnectedToNodes())
    #
    # op = {"dest": "06b9a6eacd7a77b9361123fd19776455"
    #               "eb16b9c83426a1abbf514a414792b73f",
    #       "txnType": ADD_ATTR}
    #
    # client1.submit(op)
    #
    # op = {"txnType": ADD_NYM, 'ADDadd_nym, nym: bb1cb802, role: SPONSOR}
    #
    # def chk():
    #     assert len(client1.getTxnsByAttribute("name")) == 3
    #     assert len(client1.getTxnsByAttribute("age")) == 2
    #
    # looper.run(eventually(chk, retryWait=1, timeout=10))


# def testSponsorCreatesAnAttribute(client1, looper):
#     op = {"dest": "06b9a6eacd7a77b9361123fd19776455"
#                   "eb16b9c83426a1abbf514a414792b73f",
#           "txnType": ADD_ATTR}
#     client1.submit(op)
#
#     def chk():
#         assert len(client1.getTxnsByAttribute("name")) == 3
#         assert len(client1.getTxnsByAttribute("age")) == 2
#
#     looper.run(eventually(chk, retryWait=1, timeout=10))
#
#
#


def testTxnRetrievalByAttributeName(client1, looper):
    # TODO: These are dummy transactions, just to verify the client retrieval
    #  is working correctly
    operations = [{DATA:
                       "06b9a6eacd7a77b9361123fd19776455eb16b9c83426a1abbf514a414792b73f", TXN_TYPE: ADD_ATTR, TARGET_NYM: 'n/a'},
                  {DATA:
                       "6f186f0b9303e2affde0b5d5e6586a633460a224b2a47f2a645cd5674185cf0b", TXN_TYPE: ADD_ATTR, TARGET_NYM: 'n/a'},
                  {DATA:
                       "6f186f0b9303e2affde0b5d7f2a645cd5674185cf0b5e6586a633460a224b2a4", TXN_TYPE: ADD_ATTR, TARGET_NYM: 'n/a'},
                  {ROLE:
                       "6f4b6612125fb3a0daecd2799dfd6c9c299424fd920f9b308110a2c1fbd8f443", TXN_TYPE: ADD_ATTR, TARGET_NYM: 'n/a'},
                  {ROLE:
                       "6f4b6612125fba2c1fbd8f4433a0daecd2799dfd6c9c299424fd920f9b308110", TXN_TYPE: ADD_ATTR, TARGET_NYM: 'n/a'}]

    client1.submit(*operations)

    def chk():
        assert len(client1.getTxnsByAttribute(DATA)) == 3
        assert len(client1.getTxnsByAttribute(ROLE)) == 2

    looper.run(eventually(chk, retryWait=1, timeout=10))



