from anoncreds.protocol.prover import Prover
from anoncreds.protocol.utils import generateMasterSecret, generateVPrime


class ProverWallet():
    def __init__(self):
        self._masterSecret = None
        self._vprimes = {}

    @property
    def masterSecret(self):
        if not self._masterSecret:
            self._masterSecret = generateMasterSecret()
        return self._masterSecret

    def getVPrimes(self, *keys):
        # result = {}
        # for key in keys:
        #     if key not in self._vprimes:
        #         self._vprimes[key] = generateVPrime()
        #     result[key] = self._vprimes[key]
        # return result
        return Prover.getVPrimes(self, *keys)
