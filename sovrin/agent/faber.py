from typing import Dict

import os
from plenum.common.looper import Looper
from plenum.common.txn import TYPE, NAME

from plenum.common.util import getlogger, randomString
from plenum.test.helper import genHa
from sovrin.agent.agent import Agent, WalletedAgent
from sovrin.agent.msg_types import ACCEPT_INVITE, REQUEST_CLAIMS, \
    CLAIM_NAME_FIELD
from sovrin.client.client import Client
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.util import getConfig

logger = getlogger()


CLAIMS_LIST = [{
    "name": "Transcript",
    "version": "1.2",
    "claimDefSeqNo": "<claimDefSeqNo>",
    "values": {
        "student_name": "Alice Garcia",
        "ssn": "123456789",
        "degree": "Bachelor of Science, Marketing",
        "year": "2015",
        "status": "graduated"
    }
}]

AVAILABLE_CLAIMS_LIST = [{
    "name": "Transcript",
    "version": "1.2",
    "claimDefSeqNo": "<claimDefSeqNo>",
    "definition": {
        "attributes": {
            "student_name": "string",
            "ssn": "int",
            "degree": "string",
            "year": "string",
            "status": "string"
        }
    }
}]


class FaberAgent(WalletedAgent):
    def __init__(self,
                 basedirpath: str,
                 client: Client=None,
                 wallet: Wallet=None,
                 port: int=None,
                 handlers: Dict=None):
        if not basedirpath:
            config = getConfig()
            basedirpath = basedirpath or os.path.expanduser(config.baseDir)

        super().__init__('Faber College', basedirpath, client, wallet, port)
        self.handlers = handlers

    def handleEndpointMessage(self, msg):
        body, frm = msg
        typ = body.get(TYPE)
        handler = self.handlers.get(typ)
        if handler:
            frmHa = self.endpoint.getRemote(frm).ha
            handler((body, (frm, frmHa)))
        else:
            logger.warning("no handler found for type {}".format(typ))


def runFaber(name=None, wallet=None, basedirpath=None, startRunning=True):
    _, port = genHa()
    _, clientPort = genHa()
    client = Client(randomString(6),
                    ha=("0.0.0.0", clientPort),
                    basedirpath=basedirpath)

    def reqClaim(msg):
        body, (frm, ha) = msg
        link = faber.verifyAndGetLink(msg)
        if link:
            body, (frm, ha) = msg
            claimName = body[CLAIM_NAME_FIELD]
            claimsToSend = []
            for cl in CLAIMS_LIST:
                if cl[NAME] == claimName:
                    claimsToSend.append(cl)

            resp = faber.createClaimsMsg(claimsToSend)
            faber.signAndSendToCaller(resp, link.localIdentifier, frm)
        else:
            raise NotImplementedError

    def acceptInvite(msg):
        link = faber.verifyAndGetLink(msg)
        if link:
            body, (frm, ha) = msg
            resp = faber.createAvailClaimListMsg(AVAILABLE_CLAIMS_LIST)
            faber.signAndSendToCaller(resp, link.localIdentifier, frm)

        # TODO: If I have the below exception thrown, somehow the
        # error msg which is sent in verifyAndGetLink is not being received
        # on the other end, so for now, commented, need to come back to this
        # else:
        #     raise NotImplementedError

    handlers = {
        ACCEPT_INVITE: acceptInvite,
        REQUEST_CLAIMS: reqClaim
    }

    faber = FaberAgent(name, wallet=wallet, client=client, port=port,
                       handlers=handlers)
    if startRunning:
        with Looper(debug=True) as looper:
            looper.add(faber)
            logger.debug("Running Faber now...")
            looper.run()
    else:
        return faber


if __name__ == "__main__":
    runFaber()
