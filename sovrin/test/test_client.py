from plenum.test.eventually import eventually

from sovrin.common.txn import ADD_ATTR


def testTxnRetrievalByAttributeName(client1, looper):
    # TODO: These are dummy transactions, just to verify the client retrieval
    #  is working correctly
    operations = [{"name":
                       "06b9a6eacd7a77b9361123fd19776455eb16b9c83426a1abbf514a414792b73f", "txnType": ADD_ATTR},
                  {"name":
                       "6f186f0b9303e2affde0b5d5e6586a633460a224b2a47f2a645cd5674185cf0b", "txnType": ADD_ATTR},
                  {"name":
                       "6f186f0b9303e2affde0b5d7f2a645cd5674185cf0b5e6586a633460a224b2a4", "txnType": ADD_ATTR},
                  {"age":
                       "6f4b6612125fb3a0daecd2799dfd6c9c299424fd920f9b308110a2c1fbd8f443", "txnType": ADD_ATTR},
                  {"age":
                       "6f4b6612125fba2c1fbd8f4433a0daecd2799dfd6c9c299424fd920f9b308110", "txnType": ADD_ATTR}]

    client1.submit(*operations)

    def chk():
        assert len(client1.getTxnsByAttribute("name")) == 3
        assert len(client1.getTxnsByAttribute("age")) == 2

    looper.run(eventually(chk, retryWait=1, timeout=10))
