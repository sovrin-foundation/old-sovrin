import json
from collections import OrderedDict

from plenum.common.txn import TXN_TYPE, TARGET_NYM, ORIGIN, DATA, TXN_ID, TXN_TIME, \
    RAW, ENC, HASH, NAME, VERSION, TYPE, KEYS, IP, PORT, POOL_TXN_TYPES, ALIAS, \
    STEWARD, NYM
from plenum.common.types import f

ROLE = 'role'
NONCE = 'nonce'
ATTRIBUTES = "attributes"
ATTR_NAMES = "attr_names"

LAST_TXN = "lastTxn"
TXNS = "Txns"

ENC_TYPE = "encType"
SKEY = "secretKey"
REF = "ref"

allOpKeys = (TXN_TYPE, TARGET_NYM, ORIGIN, ROLE, DATA, NONCE, REF, RAW,
             ENC, HASH, ALIAS)
reqOpKeys = (TXN_TYPE,)

# Attribute Names
ENDPOINT = "endpoint"

# client transaction types
NYM = NYM
ATTRIB = "ATTRIB"
IDPROOF = "IDPROOF"
ASSIGN_AGENT = "ASSIGN_AGENT"
ADD_SPONSOR = "ADD_SPONSOR"
ADD_AGENT = "ADD_AGENT"
DISCLO = "DISCLO"
GET_ATTR = "GET_ATTR"
GET_NYM = "GET_NYM"
GET_TXNS = "GET_TXNS"
GET_TXN = "GET_TXN"
CRED_DEF = "CRED_DEF"
GET_CRED_DEF = "GET_CRED_DEF"
ADD_PKI = "ADD_PKI"
REQ_CRED = "REQ_CRED"
GET_NONCE = "GET_NONCE"
VER_PRF = "VER_PRF"
ISSUER_KEY = "ISSUER_KEY"
GET_ISSUER_KEY = "GET_ISSUER_KEY"

# Temp for demo
GEN_CRED = "GEN_CRED"

openTxns = (GET_NYM, GET_ATTR, GET_CRED_DEF, GET_ISSUER_KEY)


# TXN_TYPE -> (requireds, optionals)
fields = {NYM: ([TARGET_NYM], [ROLE]),
          ATTRIB: ([], [RAW, ENC, HASH]),
          CRED_DEF: ([NAME, VERSION, ATTR_NAMES], [TYPE, ]),
          GET_CRED_DEF: ([], []),
          ISSUER_KEY: ([REF, DATA]),
          GET_ISSUER_KEY: ([REF, ORIGIN])
          }

validTxnTypes = {NYM,
                 ATTRIB,
                 IDPROOF,
                 ASSIGN_AGENT,
                 DISCLO,
                 GET_ATTR,
                 GET_NYM,
                 GET_TXNS,
                 CRED_DEF,
                 GET_CRED_DEF,
                 ISSUER_KEY,
                 GET_ISSUER_KEY}
validTxnTypes.update(POOL_TXN_TYPES)


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


def AddNym(target, role=None):
    return newTxn(txnType=NYM, target=target, role=role)


def AddAttr(target, attrData, role=None):
    return newTxn(txnType=ATTRIB, target=target, role=role,
                  enc=attrData)


def GetAttr(target, attrName, role=None):
    queryData = json.dumps({"name": attrName})
    return newTxn(txnType=GET_ATTR, target=target, role=role,
                  data=queryData)


# TODO: Change name to txn or some thing else after discussion
def newTxn(txnType, target=None, data=None, enc=None, raw=None,
           hash=None, role=None):
    txn = {
        TXN_TYPE: txnType
    }
    if target:
        txn[TARGET_NYM] = target
    if data:
        txn[DATA] = data
    if enc:
        txn[ENC] = enc
    if raw:
        txn[RAW] = raw
    if hash:
        txn[HASH] = hash
    if role:
        txn[ROLE] = role
    return txn

# TODO: Move them to a separate file
# ROLE types
STEWARD = STEWARD
SPONSOR = "SPONSOR"
USER = "USER"


def getGenesisTxns():
    return [
        {ALIAS: "Steward1", TARGET_NYM: "SAdaWX5yGhVuLgeZ3lzAxTJNxufq8c3UYlCGjsUyFd0=", TXN_ID: "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b", TXN_TYPE: NYM, ROLE: STEWARD},
        {ALIAS: "Steward2", TARGET_NYM: "F8t5+ytBIPKx7GXkGY1uCLKOgT/rAeSkAIObheGAgM4=", TXN_ID: "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4c", TXN_TYPE: NYM, ROLE: STEWARD},
        {ALIAS: "Steward3", TARGET_NYM: "ptJFXqOldxq6n8sDeSQRTJL58yUEn2tCaec52QSLuGk=", TXN_ID: "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4d", TXN_TYPE: NYM, ROLE: STEWARD},
        {ALIAS: "Steward4", TARGET_NYM: "LISK2GZO5lHkiWwTqEqJopZKyl63eouIHmDe1cgbTp0=", TXN_ID: "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4e", TXN_TYPE: NYM, ROLE: STEWARD},
        {ALIAS: "Steward5",  TARGET_NYM: "Lwp7KfU2UgBc1HIKP+es0IyFpOKc1vSNGQXidtrG/+8=", TXN_ID: "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4f", TXN_TYPE: NYM, ROLE: STEWARD},
        {ALIAS: "Steward6", TARGET_NYM: "NLTZBDFWy23PC+sKKUm3VZyUDSvLbb6MU6mzAnjjp0Y=", TXN_ID: "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b50", TXN_TYPE: NYM, ROLE: STEWARD},
        {ALIAS: "Steward7", TARGET_NYM: "1i8Bah79Hk/feT60LNhEceG6nwzwTRKHtcxx9hYofLg=", TXN_ID: "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b51", TXN_TYPE: NYM, ROLE: STEWARD},
        {TXN_TYPE: NYM, TARGET_NYM: 'xRuFk+Z8yWFVRvf1Z4JWe1f82Ew3nmr73ghN2oS9PVI=', ROLE: STEWARD, TXN_ID: '6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b'},
        {TXN_TYPE: NYM, f.IDENTIFIER.nm: 'xRuFk+Z8yWFVRvf1Z4JWe1f82Ew3nmr73ghN2oS9PVI=', TARGET_NYM: 'o7z4QmFkNB+mVkFI2BwX0Hdm1BGhnz8psWnKYIXWTaQ=', ROLE: SPONSOR, TXN_ID: '6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4c'},
        {TXN_TYPE: NYM, TARGET_NYM: 'OP2h59vBVQerRi6FjoOoMhSTv4CAemeEg4LPtDHaEWw=', TXN_ID: '50c2f66f7fda2ece684d1befc667e894b4460cb782f5387d864fa7d5f14c4066', ROLE: SPONSOR, f.IDENTIFIER.nm: 'xRuFk+Z8yWFVRvf1Z4JWe1f82Ew3nmr73ghN2oS9PVI='},
        {TXN_TYPE: NYM, TARGET_NYM: 'adityastaging', TXN_ID: '77c2f66f7fda2ece684d1befc667e894b4460cb782f5387d864fa7d5f14c4066', f.IDENTIFIER.nm: 'OP2h59vBVQerRi6FjoOoMhSTv4CAemeEg4LPtDHaEWw='},
        {TXN_TYPE: NYM, TARGET_NYM: 'iosstaging', TXN_ID: '91c2f66f7fda2ece684d1befc667e894b4460cb782f5387d864fa7d5f14c4066', f.IDENTIFIER.nm: 'OP2h59vBVQerRi6FjoOoMhSTv4CAemeEg4LPtDHaEWw='},
        {ALIAS: "Steward8", TARGET_NYM: "V+jbY0Fniz7xFzYIrRYeVQZeDeGHrlB3fwCPEwvicqI=", TXN_ID: "4770beb7e45bf623bd9987af4bd6d6d8eb8b68a4d00fa2a4c6b6f3f0c1c036f8", TXN_TYPE: NYM, ROLE: STEWARD},
    ]

def getGenesisTxnsForLocal():
    return [{ALIAS: "Steward1",
             TARGET_NYM: "SAdaWX5yGhVuLgeZ3lzAxTJNxufq8c3UYlCGjsUyFd0=",
             TXN_ID:
                 "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b",
             TXN_TYPE: NYM, ROLE: STEWARD},
            {ALIAS: "Steward2",
             TARGET_NYM: "F8t5+ytBIPKx7GXkGY1uCLKOgT/rpool_AeSkAIObheGAgM4=",
             TXN_ID:
                 "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4c",
             TXN_TYPE: NYM, ROLE: STEWARD},
            {ALIAS: "Steward3",
             TARGET_NYM: "ptJFXqOldxq6n8sDeSQRTJL58yUEn2tCaec52QSLuGk=",
             TXN_ID:
                 "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4d",
             TXN_TYPE: NYM, ROLE: STEWARD},
            {ALIAS: "Steward4",
             TARGET_NYM: "LISK2GZO5lHkiWwTqEqJopZKyl63eouIHmDe1cgbTp0=",
             TXN_ID:
                 "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4e",
             TXN_TYPE: NYM, ROLE: STEWARD},
            {ALIAS: "Alice",
             TARGET_NYM: "Lwp7KfU2UgBc1HIKP+es0IyFpOKc1vSNGQXidtrG/+8=",
             "identifier": "SAdaWX5yGhVuLgeZ3lzAxTJNxufq8c3UYlCGjsUyFd0=",
             TXN_ID:
                 "e7f6c011776e8db7cd330b54174fd76f7d0216b612387a5ffcfb81e6f0919683",
             TXN_TYPE: NYM},
            {ALIAS: "Jason",
             TARGET_NYM: "LfBBJfABWvtHzoU674dyCU/5SYwUyxueEpc8KSfaD6Y=",
             "identifier": "SAdaWX5yGhVuLgeZ3lzAxTJNxufq8c3UYlCGjsUyFd0=",
             TXN_ID:
                 "e7f6c011776e8db7cd330b54174fd76f7d0216b612387a5ffcfb81e6f0919684",
             TXN_TYPE: NYM},
            {ALIAS: "John",
             TARGET_NYM: "K8KACzMW4Akgn/11fasZzPCuhLx66QZU4egXEtJw9lM=",
             "identifier": "SAdaWX5yGhVuLgeZ3lzAxTJNxufq8c3UYlCGjsUyFd0=",
             TXN_ID:
                 "e7f6c011776e8db7cd330b54174fd76f7d0216b612387a5ffcfb81e6f0919685",
             TXN_TYPE: NYM},
            {ALIAS: "Les",
             TARGET_NYM: "NLTZBDFWy23PC+sKKUm3VZyUDSvLbb6MU6mzAnjjp0Y=",
             "identifier": "SAdaWX5yGhVuLgeZ3lzAxTJNxufq8c3UYlCGjsUyFd0=",
             TXN_ID: "e7f6c011776e8db7cd330b54174fd76f7d0216b612387a5ffcfb81e6f0919686",
             TXN_TYPE: NYM}]


def getTxnOrderedFields():
    return OrderedDict([
        (f.IDENTIFIER.nm, (str, str)),
        (f.REQ_ID.nm, (str, int)),
        (TXN_ID, (str, str)),
        (TXN_TIME, (str, float)),
        (TXN_TYPE, (str, str)),
        (TARGET_NYM, (str, str)),
        (DATA, (str, str)),
        (ALIAS, (str, str)),
        (RAW, (str, str)),
        (ENC, (str, str)),
        (HASH, (str, str)),
        (ROLE, (str, str)),
        (REF, (str, str))
    ])


def isValidRole(role):
    return role in (STEWARD, SPONSOR, USER)
