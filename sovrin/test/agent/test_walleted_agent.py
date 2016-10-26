from functools import partial

from ledger.util import F
from plenum.common.log import getlogger
from sovrin.agent.agent import WalletedAgent
from sovrin.common.util import ensureReqCompleted
from sovrin.test.agent.helper import getAgentCmdLineParams

logger = getlogger()


class TestWalletedAgent(WalletedAgent):
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

            # TODO: Refactor ASAP
            def dummy(r, e):
                logger.debug("Issuer key written on ledger")
                if clbk:
                    logger.debug("Calling the callback")
                    clbk()

            self.loop.call_later(.2, ensureReqCompleted, self.loop,
                                 req.reqId, self.client,
                                 dummy, None, None,
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
                                 req.reqId, self.client,
                                 postClaimDefWritten, (claimDef,), None,
                                 chk)
