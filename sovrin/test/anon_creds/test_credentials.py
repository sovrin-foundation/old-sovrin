import json

import pytest

from anoncreds.protocol.types import SerFmt
from plenum.common.txn import TXN_TYPE, NAME, VERSION, DATA, TARGET_NYM, \
    KEYS
from plenum.test.eventually import eventually
from plenum.test.helper import checkSufficientRepliesRecvd
from sovrin.common.txn import GET_CRED_DEF, ATTR_NAMES


@pytest.fixture(scope="module")
def curiousClient(userWalletA, nodeSet, looper, tdir):
    from sovrin.test.helper import genTestClient
    client, _ = genTestClient(nodeSet, tmpdir=tdir)
    client.registerObserver(userWalletA.handleIncomingReply)
    looper.add(client)
    looper.run(client.ensureConnectedToNodes())
    return client


def testIssuerWritesCredDef(credentialDefinitionAdded):
    """
    A credential definition is added
    """
    pass


def testIssuerWritesPublicKey(issuerPublicKeysAdded):
    """
    An issuer key is added
    """
    pass


def testProverGetsCredDef(credentialDefinitionAdded, userWalletA, tdir,
                          nodeSet, looper, sponsorWallet, credDef, curiousClient):
    """
    A credential definition is received
    """

    # Don't move below import outside of this method
    # else that client class doesn't gets reloaded
    # and hence it doesn't get updated with correct plugin class/methods
    # and it gives error (for permanent solution bug is created: #130181205).
    # from sovrin.test.helper import genTestClient
    #

    definition = credDef.get(serFmt=SerFmt.base58)
    credDefKey = (definition[NAME], definition[VERSION],
                  sponsorWallet.defaultId)
    req = userWalletA.requestCredDef(credDefKey, userWalletA.defaultId)
    curiousClient.submitReqs(req)

    looper.run(eventually(checkSufficientRepliesRecvd, curiousClient.inBox,
                          req.reqId, nodeSet.f,
                          retryWait=1, timeout=5))
    reply, status = curiousClient.getReply(req.reqId)
    assert status == "CONFIRMED"
    recvdCredDef = json.loads(reply[DATA])
    assert recvdCredDef[NAME] == definition[NAME]
    assert recvdCredDef[VERSION] == definition[VERSION]
    assert recvdCredDef[ATTR_NAMES].split(",") == definition[ATTR_NAMES]
    # TODO: Check whether cred def is added to wallet and then compare cred def
    # retrieved from wallet


def testGetIssuerKey(credentialDefinitionAdded, userWalletA, tdir,
                          nodeSet, looper, sponsorWallet, credDef,
                     issuerPublicKeysAdded, curiousClient):
    # TODO: Complete this
    key = (sponsorWallet.defaultId, credentialDefinitionAdded)
    req = userWalletA.requestIssuerKey(key,
                                       userWalletA.defaultId)
    curiousClient.submitReqs(req)
    looper.run(eventually(checkSufficientRepliesRecvd, curiousClient.inBox,
                          req.reqId, nodeSet.f,
                          retryWait=1, timeout=5))
    reply, status = curiousClient.getReply(req.reqId)
    assert status == "CONFIRMED"
    assert userWalletA.getIssuerPublicKey(key).seqNo

