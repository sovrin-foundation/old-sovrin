import json

import pytest
from ledger.util import F

from anoncreds.protocol.types import SerFmt
from plenum.common.txn import NAME, VERSION, DATA
from plenum.test.eventually import eventually
from plenum.test.helper import checkSufficientRepliesRecvd
from sovrin.common.txn import ATTR_NAMES


@pytest.fixture(scope="module")
def curiousClient(userWalletA, nodeSet, looper, tdir):
    from sovrin.test.helper import genTestClient
    client, _ = genTestClient(nodeSet, tmpdir=tdir)
    client.registerObserver(userWalletA.handleIncomingReply)
    looper.add(client)
    looper.run(client.ensureConnectedToNodes())
    return client


def testIssuerWritesCredDef(claimDefinitionAdded):
    """
    A credential definition is added
    """
    pass


def testIssuerWritesPublicKey(issuerPublicKeysAdded):
    """
    An issuer key is added
    """
    pass


def testProverGetsCredDef(claimDefinitionAdded, userWalletA, tdir,
                          nodeSet, looper, sponsorWallet, claimDef, curiousClient):
    """
    A credential definition is received
    """

    # Don't move below import outside of this method
    # else that client class doesn't gets reloaded
    # and hence it doesn't get updated with correct plugin class/methods
    # and it gives error (for permanent solution bug is created: #130181205).

    definition = claimDef.get(serFmt=SerFmt.base58)
    credDefKey = (definition[NAME], definition[VERSION],
                  sponsorWallet.defaultId)
    req = userWalletA.requestClaimDef(credDefKey, userWalletA.defaultId)
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
    claimDef = userWalletA.getClaimDef(seqNo=recvdCredDef[F.seqNo.name])
    assert claimDef.attrNames == definition[ATTR_NAMES]


def testGetIssuerKey(claimDefinitionAdded, userWalletA, tdir,
                     nodeSet, looper, sponsorWallet, claimDef,
                     issuerPublicKeysAdded, curiousClient):
    key = (sponsorWallet.defaultId, claimDefinitionAdded)
    req = userWalletA.requestIssuerKey(key,
                                       userWalletA.defaultId)
    curiousClient.submitReqs(req)
    looper.run(eventually(checkSufficientRepliesRecvd, curiousClient.inBox,
                          req.reqId, nodeSet.f,
                          retryWait=1, timeout=5))
    reply, status = curiousClient.getReply(req.reqId)
    assert status == "CONFIRMED"
    assert userWalletA.getIssuerPublicKey(key).seqNo

