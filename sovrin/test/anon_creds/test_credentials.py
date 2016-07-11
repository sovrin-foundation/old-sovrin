import json

from anoncreds.protocol.types import SerFmt
from plenum.common.txn import ORIGIN, TXN_TYPE, NAME, VERSION, DATA, TARGET_NYM, \
    KEYS
from plenum.test.eventually import eventually
from plenum.test.helper import checkSufficientRepliesRecvd
from sovrin.common.txn import GET_CRED_DEF
from sovrin.test.helper import genTestClient


def testIssuerWritesCredDef(credentialDefinitionAdded):
    """
    A credential definition is added
    """
    pass


def testProverGetsCredDef(credentialDefinitionAdded, userSignerA, tdir,
                          nodeSet, looper, sponsorSigner, credDef):
    """
    A credential definition is received
    """
    user = genTestClient(nodeSet, signer=userSignerA, tmpdir=tdir)
    looper.add(user)
    looper.run(user.ensureConnectedToNodes())
    definition = credDef.get(serFmt=SerFmt.base58)
    op = {
        TARGET_NYM: sponsorSigner.verstr,
        TXN_TYPE: GET_CRED_DEF,
        DATA: {
            NAME: definition[NAME],
            VERSION: definition[VERSION]
        }
    }
    req, = user.submit(op, identifier=userSignerA.verstr)
    looper.run(eventually(checkSufficientRepliesRecvd, user.inBox,
                          req.reqId, nodeSet.f,
                          retryWait=1, timeout=5))
    reply, status = user.getReply(req.reqId)
    assert status == "CONFIRMED"
    recvdCredDef = json.loads(reply[DATA])
    assert recvdCredDef[NAME] == definition[NAME]
    assert recvdCredDef[VERSION] == definition[VERSION]
    assert json.loads(recvdCredDef[KEYS]) == definition[KEYS]
    # TODO: Check whether cred def is added to wallet and then compare cred def
    # retrieved from wallet
