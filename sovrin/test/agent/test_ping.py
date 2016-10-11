import pytest
from plenum.common.txn import TYPE, NONCE, IDENTIFIER

from plenum.common.types import f
from plenum.test.eventually import eventually
from sovrin.agent.agent import WalletedAgent
from sovrin.agent.msg_types import ACCEPT_INVITE, AVAIL_CLAIM_LIST

from sovrin.test.agent.helper import ensureAgentsConnected


def testPing(aliceAcceptedFaber, faberIsRunning, aliceAgent):
    aliceAgent.sendPing('FaberCollege')

    # msg = WalletedAgent.createAvailClaimListMsg(faber.getAvailableClaimList())
    # sig = aliceCli.activeWallet.signMsg(msg)
    # msg[IDENTIFIER] = faberCli.activeWallet.defaultId
    # msg[f.SIG.nm] = sig
    # msg[TYPE] = AVAIL_CLAIM_LIST


