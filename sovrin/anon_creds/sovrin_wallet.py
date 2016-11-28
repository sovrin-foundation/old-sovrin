from anoncreds.protocol.repo.public_repo import PublicRepo
from anoncreds.protocol.types import ClaimDefinition, ID
from anoncreds.protocol.wallet.wallet import Wallet

from sovrin.anon_creds.sovrin_public_repo import SovrinPublicRepo


class SovrinWallet(Wallet):
    def __init__(self, id, repo: SovrinPublicRepo):
        Wallet.__init__(self, id, repo)

        # claim def dicts
        self._claimDefsByKey = {}
        self._claimDefsById = {}

        # other dicts with key=claimDefKey
        self._pks = {}
        self._pkRs = {}
        self._accums = {}
        self._accumPks = {}
        self._tails = {}

    # GET

    def getClaimDef(self, id: ID) -> ClaimDefinition:
        if id.claimDefKey and id.claimDefKey in self._claimDefsByKey:
            return self._claimDefsByKey[id.claimDefKey]
        if id.claimDefId and id.claimDefId in self._claimDefsById:
            return self._claimDefsById[id.claimDefId]

        claimDef = self._repo.getClaimDef(id)
        if not claimDef:
            raise ValueError('No claim definition with ID={} and key={}'.format(id.claimDefId, id.claimDefKey))

        self._cacheClaimDef(claimDef)

        return claimDef

    @abstractmethod
    def getAllClaimDef(self) -> Sequence[ClaimDefinition]:
        return self._claimDefsByKey.values()

    def getPublicKey(self, id: ID) -> PublicKey:
        return self._getValueForId(self._pks, id, self._repo.getPublicKey)

    def getPublicKeyRevocation(self, id: ID) -> RevocationPublicKey:
        return self._getValueForId(self._pkRs, id, self._repo.getPublicKeyRevocation)

    def getPublicKeyAccumulator(self, id: ID) -> AccumulatorPublicKey:
        return self._getValueForId(self._accumPks, id, self._repo.getPublicKeyAccumulator)

    def getAccumulator(self, id: ID) -> Accumulator:
        return self._getValueForId(self._accums, id, self._repo.getAccumulator)

    def getTails(self, id: ID) -> TailsType:
        return self._getValueForId(self._tails, id, self._repo.getTails)

    def updateAccumulator(self, id: ID, ts=None, seqNo=None):
        acc = self._repo.getAccumulator(id)
        self._cacheValueForId(self._accums, id, acc)

    def shouldUpdateAccumulator(self, id: ID, ts=None, seqNo=None):
        # TODO
        return True

    # HELPER

    def _getValueForId(self, dict: Dict[ClaimDefinitionKey, Any], id: ID, getFromRepo=None) -> Any:
        claimDef = self.getClaimDef(id)
        claimDefKey = claimDef.getKey()

        if claimDefKey in dict:
            return dict[claimDefKey]

        value = None
        if getFromRepo:
            id.claimDefKey = claimDefKey
            id.claimDefId = claimDef.id
            value = getFromRepo(id)

        if not value:
            raise ValueError(
                'No value for claim definition with ID={} and key={}'.format(id.claimDefId, id.claimDefKey))

        dict[claimDefKey] = value
        return value

    def _cacheValueForId(self, dict: Dict[ClaimDefinitionKey, Any], id: ID, value: Any):
        claimDefKey = self.getClaimDef(id).getKey()
        dict[claimDefKey] = value

    def _cacheClaimDef(self, claimDef: ClaimDefinition):
        self._claimDefsByKey[claimDef.getKey] = claimDef
        if claimDef.id:
            self._claimDefsById[claimDef.id] = claimDef
