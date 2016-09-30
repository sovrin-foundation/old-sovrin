import json
from typing import Dict

import os

from plenum.common.log import getlogger
from plenum.common.looper import Looper
from plenum.common.txn import TYPE
from plenum.common.util import randomString
from plenum.test.helper import genHa
from sovrin.agent.agent import Agent
from sovrin.agent.helper import processInvAccept
from sovrin.agent.msg_types import ACCEPT_INVITE, AVAIL_CLAIM_LIST
from sovrin.client.client import Client
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


class AliceAgent(Agent):
    def __init__(self, name: str, basedirpath, client: Client=None, port: int=None,
                 handlers: Dict=None):
        super().__init__(name, basedirpath, client, port,)
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
        if not handler:
            handler(body)
        else:
            logger.debug("no handler found for type")


def runAlice(name=None, wallet=None, basedirpath=None, port=None,
             startRunning=True):
    # TODO: Copied code from `runFaber`, need to refactor
    name = name or 'Alice Jones'
    wallet = wallet or Wallet(name)
    config = getConfig()
    basedirpath = basedirpath or os.path.expanduser(config.baseDir)
    if not port:
        _, port = genHa()
    _, clientPort = genHa()
    client = Client(randomString(6),
                    ha=("0.0.0.0", clientPort),
                    basedirpath=basedirpath)

    def listClaims(msg):
        body, frm = msg
        """
        body = {
            "type": <some type>,
            "identifier": <id>,
            "nonce": <nonce>,
            "signature" : <sig>
        }
        """
        # TODO: Need to do nonce verification here
        data = json.loads(body)
        print(data)
        # wallet.knownIds[data['identifier']] =
        # TODO: Send claims

    handlers = {
        AVAIL_CLAIM_LIST: listClaims
    }

    alice = AliceAgent(name,
                       basedirpath=basedirpath,
                       client=client,
                       port=port,
                       handlers=handlers)
    if startRunning:
        with Looper(debug=True) as looper:
            looper.add(alice)
            logger.debug("Running Faber now...")
            looper.run()
    else:
        return alice


if __name__ == "__main__":
    runAlice()
