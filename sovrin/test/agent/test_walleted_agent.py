from functools import partial

from ledger.util import F
from sovrin.agent.agent import WalletedAgent
from sovrin.common.util import getCredDefIsrKeyAndExecuteCallback, \
    ensureReqCompleted


class TestWalletedAgent(WalletedAgent):
    def addCredDefAndIskIfNotFoundOnLedger(self, name, version, origin,
                                           attrNames, typ,
                                           credDefSecretKey=None, clbk=None):
        claimDefKey = (name, version, origin)

        def postClaimDefWritten(reply, error, claimDef):
            claimDefSeqNo = reply.get(F.seqNo.name)
            self.wallet.createIssuerKey(claimDefSeqNo=claimDefSeqNo,
                                 claimDef=claimDef, csk=credDefSecretKey)
            req, = self.wallet.preparePending()
            self.client.submitReqs(req)
            chk = partial(self.wallet.isIssuerKeyComplete,
                          self.wallet.defaultId, claimDefSeqNo)

            # TODO: Refactor ASAP
            def dummy(r, e):
                if clbk:
                    clbk()

            self.loop.call_later(.2, ensureReqCompleted, self.loop,
                                 req.reqId, self.client,
                                 dummy, None, None,
                                 chk)

        credDef = self.wallet.getClaimDef(key=claimDefKey)
        chk = partial(self.wallet.isClaimDefComplete, claimDefKey)
        if chk():
            # # Assuming if credential definition is present on ledger the
            # # issuer key would be
            issuerPubKey = self.wallet.getIssuerPublicKey(key=(
                origin, credDef.seqNo))
            clbk()
        else:
            claimDef = self.wallet.createClaimDef(name=name, version=version,
                                attrNames=attrNames, typ=typ)
            req, = self.wallet.preparePending()
            self.client.submitReqs(req)
            self.loop.call_later(.2, ensureReqCompleted, self.loop,
                                 req.reqId, self.client,
                                 postClaimDefWritten, (claimDef, ), None,
                                 chk)