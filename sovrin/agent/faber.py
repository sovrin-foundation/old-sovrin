import json

from plenum.common.looper import Looper
from plenum.common.txn import TYPE
from plenum.common.util import getlogger
from plenum.test.helper import genHa
from sovrin.agent.agent import Agent
from sovrin.agent.msg_types import ACCEPT_INVITE
from sovrin.client.client import Client
from sovrin.client.wallet.wallet import Wallet


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


name = "Faber College"
wallet = Wallet(name)


class FaberAgent(Agent):
    def __init__(self, name: str="agent1", client: Client=None, port: int=None):
        super().__init__(name, client, port)
        self.handlers = {
            ACCEPT_INVITE: self.acceptInvite
        }

    def handleEndpointMessage(self, msg):
        typ = msg.get(TYPE)
        handler = self.handlers.get(typ)
        if not handler:
            handler(msg)
        else:
            logger.debug("no handler found for type")

    def acceptInvite(self, msg):
        body, frm = msg
        """
        body = {
            "type": <some type>,
            "identifier": <id>,
            "nonce": <nonce>,
            "signature" : <sig>
        }
        """
        # TODO: Need to nonce verification here
        data = json.loads(body)
        # wallet.knownIds[data['identifier']] =
        # TODO: Send claims



def runFaber():
    _, port = genHa()
    client = Client(name=name)
    faber = FaberAgent(name, client=client, port=port)

    with Looper(debug=True) as looper:
        looper.add(faber)
        logger.debug("Running Faber now...")
        looper.run()