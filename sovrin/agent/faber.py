import json
from typing import Dict

import os
from plenum.common.looper import Looper
from plenum.common.txn import TYPE
from plenum.common.types import f
from plenum.common.util import getlogger, randomString
from plenum.test.helper import genHa
from sovrin.agent.agent import Agent
from sovrin.agent.helper import processInvAccept
from sovrin.agent.msg_types import ACCEPT_INVITE
from sovrin.client.client import Client
from sovrin.client.wallet.helper import createAvailClaimListMsg
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.util import getConfig

logger = getlogger()


# def msgHandler(msg):
#     typ = msg.get(TYPE)
#     handler = handlers.get(typ)
#     if not handler:
#         handler(msg)
#     else:
#         logger.debug("no handler found for type")
#
#
# def acceptInvite(msg):
#     body, frm = msg
#     """
#     body = {
#         "type": <some type>,
#         "identifier": <id>,
#         "nonce": <nonce>,
#         "signature" : <sig>
#     }
#     """
#     # TODO: Need to nonce verification here
#     data = json.loads(body)
#     wallet.knownIds[data['identifier']] =
#     # TODO: Send claims
#
#
# handlers = {
#     ACCEPT_INVITE: acceptInvite
# }


class FaberAgent(Agent):
    def __init__(self, name: str="agent1", client: Client=None, port: int=None,
                 handlers: Dict=None):
        super().__init__(name, client, port, msgHandler=self.handleEndpointMessage)
        self.handlers = handlers

    @property
    def activeWallet(self):
        return self._activeWallet

    @activeWallet.setter
    def activeWallet(self, wallet):
        self._activeWallet = wallet

    def handleEndpointMessage(self, msg):
        body, frm = msg
        typ = body.get(TYPE)
        handler = self.handlers.get(typ)
        if handler:
            frmHa = self.endpoint.getRemote(frm).ha
            handler((body, (frm, frmHa)))
        else:
            logger.debug("no handler found for type {}".format(typ))


def runFaber(name=None, wallet=None, basedirpath=None, startRunning=True):
    name = name or 'Faber College'
    wallet = wallet or Wallet(name)
    config = getConfig()
    basedirpath = basedirpath or os.path.expanduser(config.baseDir)
    _, port = genHa()
    _, clientPort = genHa()
    client = Client(randomString(6), ha=("0.0.0.0", clientPort),
                    basedirpath=basedirpath)

    # def f1():
    #     doSomethingWithWallet(wallet, action)
    #
    # def f2():
    #     doSomethingElseWithWallet(wallet, action2)
    #
    # handlers = {
    #     acc: f1,
    #     acd: f2
    # }

    def acceptInvite(msg):
        body, (frm, ha) = msg
        """
        body = {
            "type": <some type>,
            "identifier": <id>,
            "nonce": <nonce>,
            "signature" : <sig>
        }
        """
        # TODO: Need to do nonce verification here
        nonce = body.get("nonce")
        link = wallet.getLinkByNonce(nonce)
        if link:
            link.remoteIdentifier = body.get(f.IDENTIFIER.nm)
            link.remoteEndPoint = ha
            # TODO: Send claims
            resp = createAvailClaimListMsg(link.remoteIdentifier)
            faber.sendMessage(resp, destName=frm)

    handlers = {
        ACCEPT_INVITE: acceptInvite
    }

    faber = FaberAgent(name, client=client, port=port, handlers=handlers)
    if startRunning:
        with Looper(debug=True) as looper:
            looper.add(faber)
            logger.debug("Running Faber now...")
            looper.run()
    else:
        return faber


if __name__ == "__main__":
    runFaber()
