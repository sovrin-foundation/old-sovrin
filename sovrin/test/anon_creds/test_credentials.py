import json

from plenum.common.txn import ORIGIN, TXN_TYPE, NAME, VERSION, DATA, TARGET_NYM
from plenum.test.eventually import eventually
from plenum.test.helper import checkSufficientRepliesRecvd
from sovrin.common.txn import GET_CRED_DEF
from sovrin.test.helper import genTestClient


def testIssuerWritesCredDef(credentialDefinitionAdded):
    """
    A credential definition is added
    """
    pass


def testProverGetsCredDef(credentialDefinitionAdded, userSignerA, tdir, nodeSet,
                          looper, sponsorSigner, credDef):
    """
    A credential definition is received
    """
    user = genTestClient(nodeSet, signer=userSignerA, tmpdir=tdir)
    looper.add(user)
    looper.run(user.ensureConnectedToNodes())
    op = {
        ORIGIN: userSignerA.verstr,
        TARGET_NYM: sponsorSigner.verstr,
        TXN_TYPE: GET_CRED_DEF,
        DATA: {
            NAME: credDef[NAME],
            VERSION: credDef[VERSION]
        }
    }
    req, = user.submit(op, identifier=userSignerA.verstr)
    looper.run(eventually(checkSufficientRepliesRecvd, user.inBox, req.reqId, nodeSet.f,
               retryWait=1, timeout=5))
    reply, status = user.getReply(req.reqId)
    assert status == "CONFIRMED"
    recvdCredDef = json.loads(reply[DATA])
    assert recvdCredDef[NAME] == credDef[NAME]
    assert recvdCredDef[VERSION] == credDef[VERSION]
    # TODO: Need to check equality of keys too

