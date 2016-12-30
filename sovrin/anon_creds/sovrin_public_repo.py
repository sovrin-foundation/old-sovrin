import json

from ledger.util import F
from plenum.common.eventually import eventually
from plenum.common.exceptions import NoConsensusYet
from plenum.common.log import getlogger
from plenum.common.txn import TARGET_NYM, TXN_TYPE, DATA, NAME, VERSION, TYPE, \
    ORIGIN

from anoncreds.protocol.repo.public_repo import PublicRepo
from anoncreds.protocol.types import ClaimDefinition, ID, PublicKey, \
    RevocationPublicKey, AccumulatorPublicKey, \
    Accumulator, TailsType, TimestampType
from sovrin.common.txn import GET_CLAIM_DEF, CLAIM_DEF, ATTR_NAMES, \
    GET_ISSUER_KEY, REF, ISSUER_KEY, PRIMARY, REVOCATION
from sovrin.common.types import Request


def _ensureReqCompleted(reqKey, client, clbk):
    reply, err = client.replyIfConsensus(*reqKey)
    if reply is None:
        raise NoConsensusYet('not completed')
    return clbk(reply, err)


def _getData(result, error):
    data = json.loads(result.get(DATA).replace("\'", '"'))
    seqNo = None if not data else data.get(F.seqNo.name)
    return data, seqNo


def _submitData(result, error):
    data = json.loads(result.get(DATA).replace("\'", '"'))
    seqNo = result.get(F.seqNo.name)
    return data, seqNo


logger = getlogger()


class SovrinPublicRepo(PublicRepo):
    def __init__(self, client, wallet):
        self.client = client
        self.wallet = wallet
        self.displayer = print

    async def getClaimDef(self, id: ID) -> ClaimDefinition:
        op = {
            TARGET_NYM: id.claimDefKey.issuerId,
            TXN_TYPE: GET_CLAIM_DEF,
            DATA: {
                NAME: id.claimDefKey.name,
                VERSION: id.claimDefKey.version,
            }
        }
        try:
            data, seqNo = await self._sendGetReq(op)
        except TimeoutError:
            logger.error('Operation timed out {}'.format(op))
            return None
        return ClaimDefinition(name=data[NAME],
                               version=data[VERSION],
                               claimDefType=data[TYPE],
                               attrNames=data[ATTR_NAMES].split(","),
                               issuerId=data[ORIGIN],
                               seqId=seqNo)

    async def getPublicKey(self, id: ID) -> PublicKey:
        op = {
            TXN_TYPE: GET_ISSUER_KEY,
            REF: id.claimDefId,
            ORIGIN: id.claimDefKey.issuerId
        }

        try:
            data, seqNo = await self._sendGetReq(op)
        except TimeoutError:
            logger.error('Operation timed out {}'.format(op))
            return None

        if not data:
            return None

        data = data[DATA][PRIMARY]
        pk = PublicKey.fromStrDict(data)._replace(seqId=seqNo)
        return pk

    async def getPublicKeyRevocation(self, id: ID) -> RevocationPublicKey:
        op = {
            TXN_TYPE: GET_ISSUER_KEY,
            REF: id.claimDefId,
            ORIGIN: id.claimDefKey.issuerId
        }

        try:
            data, seqNo = await self._sendGetReq(op)
        except TimeoutError:
            logger.error('Operation timed out {}'.format(op))
            return None

        if not data:
            return None

        data = data[DATA][REVOCATION]
        pkR = RevocationPublicKey.fromStrDict(data)._replace(seqId=seqNo)
        return pkR

    async def getPublicKeyAccumulator(self, id: ID) -> AccumulatorPublicKey:
        pass

    async def getAccumulator(self, id: ID) -> Accumulator:
        pass

    async def getTails(self, id: ID) -> TailsType:
        pass

    # SUBMIT

    async def submitClaimDef(self,
                             claimDef: ClaimDefinition) -> ClaimDefinition:
        op = {
            TXN_TYPE: CLAIM_DEF,
            DATA: {
                NAME: claimDef.name,
                VERSION: claimDef.version,
                TYPE: claimDef.claimDefType,
                ATTR_NAMES: ",".join(claimDef.attrNames)
            }
        }

        try:
            data, seqNo = await self._sendSubmitReq(op)
        except TimeoutError:
            logger.error('Operation timed out {}'.format(op))
            return None

        if not seqNo:
            return None
        claimDef = claimDef._replace(issuerId=self.wallet.defaultId,
                                     seqId=seqNo)
        return claimDef

    async def submitPublicKeys(self, id: ID, pk: PublicKey,
                               pkR: RevocationPublicKey = None) -> (
            PublicKey, RevocationPublicKey):
        pkData = pk.toStrDict()
        pkRData = pkR.toStrDict()
        op = {
            TXN_TYPE: ISSUER_KEY,
            REF: id.claimDefId,
            DATA: {PRIMARY: pkData, REVOCATION: pkRData}
        }

        try:
            data, seqNo = await self._sendSubmitReq(op)
        except TimeoutError:
            logger.error('Operation timed out {}'.format(op))
            return None

        if not seqNo:
            return None
        pk = pk._replace(seqId=seqNo)
        pkR = pkR._replace(seqId=seqNo)
        return pk, pkR

    async def submitAccumulator(self, id: ID, accumPK: AccumulatorPublicKey,
                                accum: Accumulator, tails: TailsType):
        pass

    async def submitAccumUpdate(self, id: ID, accum: Accumulator,
                                timestampMs: TimestampType):
        pass

    async def _sendSubmitReq(self, op):
        return await self._sendReq(op, _submitData)

    async def _sendGetReq(self, op):
        return await self._sendReq(op, _getData)

    async def _sendReq(self, op, clbk):
        req = Request(identifier=self.wallet.defaultId, operation=op)
        req = self.wallet.prepReq(req)
        self.client.submitReqs(req)
        try:
            resp = await eventually(_ensureReqCompleted,
                                    req.key, self.client, clbk,
                                    timeout=20, retryWait=0.5)
        except NoConsensusYet:
            raise TimeoutError('Request timed out')
        return resp
