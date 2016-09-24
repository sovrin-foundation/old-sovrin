import json

from sovrin.anon_creds.cred_def import SerFmt

from plenum.common.txn import TXN_TYPE, NAME, VERSION, DATA, TARGET_NYM, \
    KEYS
from plenum.test.eventually import eventually
from plenum.test.helper import checkSufficientRepliesRecvd
from sovrin.common.txn import GET_CRED_DEF


def testIssuerWritesCredDef(credentialDefinitionAdded):
    """
    A credential definition is added
    """
    pass


def testProverGetsCredDef(credentialDefinitionAdded, userWalletA, tdir,
                          nodeSet, looper, sponsorWallet, credDef):
    """
    A credential definition is received
    """

    # Don't move below import outside of this method
    # else that client class doesn't gets reloaded
    # and hence it doesn't get updated with correct plugin class/methods
    # and it gives error (for permanent solution bug is created: #130181205).
    from sovrin.test.helper import genTestClient

    user, _ = genTestClient(nodeSet, tmpdir=tdir)
    user.registerObserver(userWalletA.handleIncomingReply)
    looper.add(user)
    looper.run(user.ensureConnectedToNodes())
    definition = credDef.get(serFmt=SerFmt.base58)
    op = {
        TARGET_NYM: sponsorWallet.defaultId,
        TXN_TYPE: GET_CRED_DEF,
        DATA: {
            NAME: definition[NAME],
            VERSION: definition[VERSION]
        }
    }
    req = userWalletA.signOp(op)
    userWalletA.pendRequest(req)
    reqs = userWalletA.preparePending()
    user.submitReqs(*reqs)

    # req, = user.submit(op, identifier=userSignerA.verstr)

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
