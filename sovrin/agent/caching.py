from sovrin.common.identity import Identity


class Caching:
    """
    Mixin for agents to manage caching.

    Dev notes: Feels strange to inherit from WalletedAgent, but self-typing
    doesn't appear to be implemented in Python yet.
    """
    def getIdentity(self, identifier):
        identity = Identity(identifier=identifier)
        req = self.wallet.requestIdentity(identity,
                                          sender=self.wallet.defaultId)
        self.client.submitReqs(req)
        return req
