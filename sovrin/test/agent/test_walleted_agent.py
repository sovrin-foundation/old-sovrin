from functools import partial

from ledger.util import F
from plenum.common.log import getlogger
from plenum.common.types import f
from plenum.test.testable import Spyable
from sovrin.agent.agent import WalletedAgent
from sovrin.common.exceptions import LinkNotFound
from sovrin.common.txn import NONCE
from sovrin.common.util import ensureReqCompleted
from sovrin.test.agent.helper import getAgentCmdLineParams

logger = getlogger()


@Spyable(
    methods=[WalletedAgent._handlePing, WalletedAgent._handlePong])
class TestWalletedAgent(WalletedAgent):

    def getLinkForMsg(self, msg):
        nonce = msg.get(NONCE)
        identifier = msg.get(f.IDENTIFIER.nm)
        link = None
        for _, li in self.wallet._links.items():
            if li.invitationNonce == nonce and li.remoteIdentifier == identifier:
                link = li
                break
        if link:
            return link
        else:
            raise LinkNotFound

    @staticmethod
    def getPassedArgs():
        return getAgentCmdLineParams()

    def addCredDefAndIskIfNotFoundOnLedger(self, name, version, origin,
                                           attrNames, typ,
                                           credDefSecretKey=None, clbk=None):
        claimDefKey = (name, version, origin)

        def postClaimDefWritten(reply, error, claimDef):
            claimDefSeqNo = reply.get(F.seqNo.name)
            logger.debug("Claim def written on ledger: {}".format(claimDef.key))
            self.wallet.createIssuerKey(claimDefSeqNo=claimDefSeqNo,
                                        claimDef=claimDef, csk=credDefSecretKey)
            req, = self.wallet.preparePending()
            self.client.submitReqs(req)
            chk = partial(self.wallet.isIssuerKeyComplete,
                          self.wallet.defaultId, claimDefSeqNo)

            # TODO: Refactor ASAP by making ensureReqCompleted's reply and
            # error optional
            def caller(r, e):
                logger.debug("Issuer key written on ledger")
                if clbk:
                    logger.debug("Calling the callback")
                    clbk()

            self.loop.call_later(.2, ensureReqCompleted, self.loop,
                                 req.key, self.client,
                                 caller, None, None,
                                 chk)

        claimDef = self.wallet.getClaimDef(key=claimDefKey)
        chk = partial(self.wallet.isClaimDefComplete, claimDefKey)
        if chk():
            # # Assuming if credential definition is present on ledger the
            # # issuer key would be
            self.wallet.getIssuerPublicKey(key=(origin, claimDef.seqNo))
            clbk()
        else:
            claimDef = self.wallet.createClaimDef(name=name, version=version,
                                                  attrNames=attrNames, typ=typ)
            req, = self.wallet.preparePending()
            self.client.submitReqs(req)
            self.loop.call_later(.2, ensureReqCompleted, self.loop,
                                 req.key, self.client,
                                 postClaimDefWritten, (claimDef,), None,
                                 chk)
