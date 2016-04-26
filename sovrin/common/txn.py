import json
from collections import OrderedDict

from plenum.common.txn import TXN_TYPE, TARGET_NYM, ORIGIN, DATA, TXN_ID, TXN_TIME
from plenum.common.types import f

NYM = "nym"

ROLE = 'role'
NONCE = 'nonce'
ATTRIBUTES = "attributes"

LAST_TXN = "lastTxn"
TXNS = "Txns"

SKEY = "secretKey"
REFERENCE = "reference"

allOpKeys = (TXN_TYPE, TARGET_NYM, ORIGIN, ROLE, DATA, NONCE, REFERENCE)
reqOpKeys = (TXN_TYPE, TARGET_NYM)

# client transaction types
ADD_NYM = "ADD_NYM"
ADD_ATTR = "ADD_ATTR"
IDPROOF = "IDPROOF"
ASSIGN_AGENT = "ASSIGN_AGENT"
ADD_SPONSOR = "ADD_SPONSOR"
ADD_AGENT = "ADD_AGENT"
DISCLOSE = "DISCLOSE"
GET_ATTR = "GET_ATTR"
GET_NYM = "GET_NYM"
GET_TXNS = "GET_TXNS"


# TXN_TYPE -> (requireds, optionals)
fields = {ADD_NYM: ([TARGET_NYM],        [ROLE]),
          ADD_ATTR: ([TARGET_NYM, DATA], [])
          }

validTxnTypes = [ADD_NYM,
                 ADD_ATTR,
                 IDPROOF,
                 ASSIGN_AGENT,
                 DISCLOSE,
                 GET_ATTR,
                 GET_NYM,
                 GET_TXNS]


# def txn(txnType,
#         targetNym,
#         origin=None,
#         data=None,
#         role=None):
#     return {
#         TXN_TYPE: txnType,
#         TARGET_NYM: targetNym,
#         ORIGIN: origin,
#         DATA: data,
#         ROLE: role
#     }


def AddNym(target, role=None, origin=None):
    return newTxn(txnType=ADD_NYM, origin=origin, target=target, role=role)


def AddAttr(target, attrData, role=None, origin=None):
    return newTxn(txnType=ADD_ATTR, origin=origin, target=target, role=role,
                  data=attrData)


def GetAttr(target, attrName, role=None, origin=None):
    queryData = json.dumps({"name": attrName})
    return newTxn(txnType=GET_ATTR, origin=origin, target=target, role=role,
                  data=queryData)


# TODO: Change name to txn or some thing else after discussion
def newTxn(txnType, origin=None, target=None, data=None, role=None):
    txn = {
        TXN_TYPE: txnType
    }
    if origin:
        txn[ORIGIN] = origin
    if target:
        txn[TARGET_NYM] = target
    if data:
        txn[DATA] = data
    if role:
        txn[ROLE] = role
    return txn

# TODO: Move them to a separate file
# ROLE types
STEWARD = "STEWARD"
SPONSOR = "SPONSOR"
USER = "USER"


def getGenesisTxns():
    t = [
        {TXN_TYPE: ADD_NYM, ORIGIN: 'aXMgYSBwaXQgYSBzZWVkLCBvciBzb21lcGluIGVsc2U=', TARGET_NYM: 'o7z4QmFkNB+mVkFI2BwX0Hdm1BGhnz8psWnKYIXWTaQ=', ROLE: SPONSOR, TXN_ID: '6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4c'},
        {TXN_TYPE: ADD_NYM, TARGET_NYM: 'OP2h59vBVQerRi6FjoOoMhSTv4CAemeEg4LPtDHaEWw=', TXN_ID: '50c2f66f7fda2ece684d1befc667e894b4460cb782f5387d864fa7d5f14c4066', ORIGIN: 'o7z4QmFkNB+mVkFI2BwX0Hdm1BGhnz8psWnKYIXWTaQ='},
        {TXN_TYPE: ADD_NYM, TARGET_NYM: 'adityastaging', TXN_ID: '77c2f66f7fda2ece684d1befc667e894b4460cb782f5387d864fa7d5f14c4066', ORIGIN: 'o7z4QmFkNB+mVkFI2BwX0Hdm1BGhnz8psWnKYIXWTaQ='},
        {TXN_TYPE: ADD_NYM, TARGET_NYM: 'iosstaging', TXN_ID: '91c2f66f7fda2ece684d1befc667e894b4460cb782f5387d864fa7d5f14c4066', ORIGIN: 'o7z4QmFkNB+mVkFI2BwX0Hdm1BGhnz8psWnKYIXWTaQ='}
    ]
    return [{
        TXN_TYPE: ADD_NYM,
        TARGET_NYM: "aXMgYSBwaXQgYSBzZWVkLCBvciBzb21lcGluIGVsc2U=",
        TXN_ID: "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b",
        ROLE: STEWARD
    }] + t


def getTxnOrderedFields():
    return OrderedDict([
        (f.IDENTIFIER.nm, (str, str)),
        (f.REQ_ID.nm, (str, int)),
        (TXN_ID, (str, str)),
        (TXN_TIME, (str, float)),
        (TXN_TYPE, (str, str)),
        (ORIGIN, (str, str)),
        (TARGET_NYM, (str, str)),
        (DATA, (str, str)),
        (ROLE, (str, str)),
        (REFERENCE, (str, str))
    ])