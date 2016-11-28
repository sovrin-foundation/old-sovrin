import json

from anoncreds.protocol.repo.public_repo import PublicRepo
from anoncreds.protocol.types import ClaimDefinition, ID, PublicKey, RevocationPublicKey, AccumulatorPublicKey, \
    Accumulator, TailsType, TimestampType
from anoncreds.protocol.utils import strToCryptoInteger
from ledger.util import F
from plenum.common.txn import TARGET_NYM, TXN_TYPE, DATA, NAME, VERSION, TYPE, ORIGIN
from plenum.test.eventually import eventually

from sovrin.common.txn import GET_CRED_DEF, CRED_DEF, ATTR_NAMES, GET_ISSUER_KEY, REF, ISSUER_KEY
from sovrin.common.types import Request
from sovrin.common.util import stringDictToCharmDict


def _ensureReqCompleted(reqKey, client, clbk):
    reply, err = client.replyIfConsensus(*reqKey)
    if reply is None:
        raise ValueError('not completed')
    return clbk(reply, err)


def _getData(result, error):
    data = json.loads(result.get(DATA).replace("\'", '"'))
    seqNo = None if not data else data.get(F.seqNo.name)
    return data, seqNo


def _submitData(result, error):
    data = json.loads(result.get(DATA).replace("\'", '"'))
    seqNo = result.get(F.seqNo.name)
    return data, seqNo


class SovrinPublicRepo(PublicRepo):
    def __init__(self, looper, client, wallet):
        self.looper = looper
        self.client = client
        self.wallet = wallet
        self.displayer = print

    def getClaimDef(self, id: ID) -> ClaimDefinition:
        op = {
            TARGET_NYM: id.claimDefKey.issuerId,
            TXN_TYPE: GET_CRED_DEF,
            DATA: {
                NAME: id.claimDefKey.name,
                VERSION: id.claimDefKey.version,
            }
        }
        data, seqNo = self._sendGetReq(op)
        return ClaimDefinition(name=data[NAME],
                               version=data[VERSION],
                               type=data[TYPE],
                               attrNames=data[ATTR_NAMES].split(","),
                               issuerId=data[ORIGIN],
                               id=seqNo)

    def getPublicKey(self, id: ID) -> PublicKey:
        op = {
            TXN_TYPE: GET_ISSUER_KEY,
            REF: id.claimDefId,
            ORIGIN: id.claimDefKey.issuerId
        }
        data, seqNo = self._sendGetReq(op)
        data = data[DATA]
        return PublicKey(N=strToCryptoInteger(data["N"]),
                         Rms=strToCryptoInteger(data["Rm1"]),
                         Rctxt=strToCryptoInteger(data["Rm2"]),
                         R=stringDictToCharmDict(data["R"]),
                         S=strToCryptoInteger(data["S"]),
                         Z=strToCryptoInteger(data["Z"]))

    def getPublicKeyRevocation(self, id: ID) -> RevocationPublicKey:
        pass

    def getPublicKeyAccumulator(self, id: ID) -> AccumulatorPublicKey:
        pass

    def getAccumulator(self, id: ID) -> Accumulator:
        pass

    def getTails(self, id: ID) -> TailsType:
        pass

    # SUBMIT

    def submitClaimDef(self, claimDef: ClaimDefinition):
        op = {
            TXN_TYPE: CRED_DEF,
            DATA: {
                NAME: claimDef.name,
                VERSION: claimDef.version,
                TYPE: claimDef.type,
                ATTR_NAMES: ",".join(claimDef.attrNames)
            }
        }

        data, seqNo = self._sendSubmitReq(op)
        claimDef.id = seqNo
        claimDef.issuerId = self.wallet.defaultId
        return claimDef

    def submitPublicKeys(self, id: ID, pk: PublicKey, pkR: RevocationPublicKey = None):
        data = {
            "N": str(pk.N),
            "R": {k: str(v) for k, v in pk.R.items()},
            "Rm1": str(pk.Rms),
            "Rm2": str(pk.Rctxt),
            "S": str(pk.S),
            "Z": str(pk.Z),

        }
        op = {
            TXN_TYPE: ISSUER_KEY,
            REF: id.claimDefId,
            DATA: data
        }

        self._sendSubmitReq(op)

    def submitAccumulator(self, id: ID, accumPK: AccumulatorPublicKey, accum: Accumulator, tails: TailsType):
        pass

    def submitAccumUpdate(self, id: ID, accum: Accumulator, timestampMs: TimestampType):
        pass

    def _sendSubmitReq(self, op):
        return self._sendReq(op, _submitData)


    def _sendGetReq(self, op):
        return self._sendReq(op, _getData)


    def _sendReq(self, op, clbk):
        req = Request(identifier=self.wallet.defaultId, operation=op)
        req = self.wallet.prepReq(req)
        self.client.submitReqs(req)

        return self.looper.run(eventually(_ensureReqCompleted,
                                          req.key, self.client, clbk,
                                          timeout=20,
                                          ratchetSteps=10))
