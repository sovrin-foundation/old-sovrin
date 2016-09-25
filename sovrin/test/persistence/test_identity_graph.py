from ledger.util import F
from plenum.common.txn import TXN_TIME
from datetime import datetime
import time

from sovrin.persistence.identity_graph import IdentityGraph


def testMakeResultTxnTimeString():
    oRecordData = {
        F.seqNo.name: 1,
        TXN_TIME: 'some-datetime'
    }
    assert TXN_TIME not in IdentityGraph.makeResult(0, oRecordData)


def testMakeResultTxnTimeDatetime():
    dt = datetime.now()
    oRecordData = {
        F.seqNo.name: 1,
        TXN_TIME: dt
    }
    assert IdentityGraph.makeResult(0, oRecordData)[TXN_TIME] == int(time.mktime(dt.timetuple()))


def testMakeResultTxnTimeNone():
    from datetime import datetime
    dt = datetime.now()
    oRecordData = {
        F.seqNo.name: 1,
    }
    assert TXN_TIME not in IdentityGraph.makeResult(0, oRecordData)
