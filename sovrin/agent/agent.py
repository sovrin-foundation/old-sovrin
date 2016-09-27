import logging
from logging import ERROR
from typing import Dict, Callable, Tuple

from plenum.common.error import fault
from plenum.common.exceptions import RemoteNotFound
from plenum.common.motor import Motor
from plenum.common.startable import Status
from plenum.common.txn import TYPE, DATA, IDENTIFIER, NONCE
from plenum.common.types import Identifier, f
from sovrin.agent.agent_net import AgentNet
from sovrin.agent.msg_types import AVAIL_CLAIM_LIST, CLAIMS
from sovrin.client.client import Client
from sovrin.client.wallet.link_invitation import SIGNATURE
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.identity import Identity
from sovrin.common.util import verifySig

CLAIMS_LIST_FIELD = 'availableClaimsList'
CLAIMS_FIELD = 'claims'
REQ_MSG = "REQ_MSG"
SIGNATURE = "signature"
ERROR = "ERROR"


class Agent(Motor, AgentNet):
    def __init__(self,
                 name: str,
                 basedirpath: str,
                 client: Client=None,
                 port: int=None,
                 msgHandler=None):
        Motor.__init__(self)
        self._name = name

        AgentNet.__init__(self,
                          name=self._name.replace(" ", ""),
                          port=port,
                          basedirpath=basedirpath,
                          msgHandler=self.handleEndpointMessage)

        # Client used to connect to Sovrin and forward on owner's txns
        self.client = client

        # known identifiers of this agent's owner
        self.ownerIdentifiers = {}  # type: Dict[Identifier, Identity]

    def name(self):
        pass

    async def prod(self, limit) -> int:
        c = 0
        if self.get_status() == Status.starting:
            self.status = Status.started
            c += 1
        if self.client:
            c += await self.client.prod(limit)
        if self.endpoint:
            c += await self.endpoint.service(limit)
        return c

    def start(self, loop):
        super().start(loop)
        if self.client:
            self.client.start(loop)
        if self.endpoint:
            self.endpoint.start()

    def _statusChanged(self, old, new):
        pass

    def onStopping(self, *args, **kwargs):
        pass

    def connect(self, network: str):
        """
        Uses the client to connect to Sovrin
        :param network: (test|live)
        :return:
        """
        raise NotImplementedError

    def syncKeys(self):
        """
        Iterates through ownerIdentifiers and ensures the keys are correct
        according to Sovrin. Updates the updated
        :return:
        """
        raise NotImplementedError

    def handleOwnerRequest(self, request):
        """
        Consumes an owner request, verifies it's authentic (by checking against
        synced owner identifiers' keys), and handles it.
        :param request:
        :return:
        """
        raise NotImplementedError

    def handleEndpointMessage(self, msg):
        pass

    def sendMessage(self, msg, destName: str=None, destHa: Tuple=None):
        try:
            remote = self.endpoint.getRemote(name=destName, ha=destHa)
        except RemoteNotFound as ex:
            fault(ex, "Do not know {} {}".format(destName, destHa))
            return
        self.endpoint.transmit(msg, remote.uid)

    def connectTo(self, ha):
        self.endpoint.connectTo(ha)


class WalletedAgent(Agent):
    """
    An agent with a self-contained wallet.

    Normally, other logic acts upon a remote agent. That other logic holds keys
    and signs messages and transactions that the Agent then forwards. In this
    case, the agent holds a wallet.
    """

    def __init__(self,
                 name: str,
                 basedirpath: str,
                 client: Client=None,
                 wallet: Wallet=None,
                 port: int=None):
        super().__init__(name, basedirpath, client, port)
        self._wallet = wallet or Wallet(name)

    @property
    def wallet(self):
        return self._wallet

    @wallet.setter
    def wallet(self, wallet):
        self._wallet = wallet

    def getErrorResponse(self, reqBody, errorMsg="Error"):
        invalidSigResp = {
            TYPE: ERROR,
            DATA: errorMsg,
            REQ_MSG: reqBody,

        }
        return invalidSigResp

    def logAndSendErrorResp(self, to, reqBody, respMsg, logMsg):
        logging.warning(logMsg)
        self.signAndSendToCaller(resp=self.getErrorResponse(reqBody, respMsg),
                                 identifier=self.wallet.defaultId, frm=to)

    def verifyAndGetLink(self, msg):
        body, (frm, ha) = msg
        key = body.get(f.IDENTIFIER.nm)
        signature = body.get(SIGNATURE)
        verified = verifySig(key, signature, body)

        nonce = body.get(NONCE)
        matchingLink = self.wallet.getLinkByNonce(nonce)

        if not verified:
            self.logAndSendErrorResp(frm, body, "Signature Rejected",
                                     "Signature verification failed for msg: {}"
                                     .format(str(msg)))
            return None

        if not matchingLink:
            self.logAndSendErrorResp(frm, body, "No Such Link found",
                                     "Link not found for msg: {}".format(msg))
            return None

        matchingLink.remoteIdentifier = body.get(f.IDENTIFIER.nm)
        matchingLink.remoteEndPoint = ha
        return matchingLink

    def signAndSendToCaller(self, resp, identifier, frm):
        resp[IDENTIFIER] = self.wallet.defaultId
        signature = self.wallet.signMsg(resp, identifier)
        resp[SIGNATURE] = signature
        self.sendMessage(resp, destName=frm)

    @staticmethod
    def getCommonMsg(type):
        msg = {}
        msg[TYPE] = type
        return msg

    @staticmethod
    def createAvailClaimListMsg(claimLists):
        msg = WalletedAgent.getCommonMsg(AVAIL_CLAIM_LIST)
        msg[CLAIMS_LIST_FIELD] = claimLists
        return msg

    @staticmethod
    def createClaimsMsg(claims):
        msg = WalletedAgent.getCommonMsg(CLAIMS)
        msg[CLAIMS_FIELD] = claims
        return msg
