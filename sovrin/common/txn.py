

TXN_TYPE = 'type'
TARGET_NYM = 'dest'
ORIGIN = 'origin'
ROLE = 'role'
DATA = 'data'

allOpKeys = [TXN_TYPE, TARGET_NYM, DATA, ROLE]

# client transaction types
ADD_NYM = "ADD_NYM"
ADD_ATTR = "ADD_ATTR"
IDPROOF = "IDPROOF"
ASSIGN_AGENT = "ASSIGN_AGENT"

# TXN_TYPE -> (requireds, optionals)
fields = {ADD_NYM: ([TARGET_NYM],        [ROLE]),
          ADD_ATTR: ([TARGET_NYM, DATA], []    )
          }

validTxnTypes = [ADD_NYM,
                 ADD_ATTR,
                 IDPROOF,
                 ASSIGN_AGENT]

def txn(txnType,
        targetId,
        sponsor=None,
        agent=None,
        data=None):
    return {
            TXN_TYPE: txnType,
            TARGET_NYM: targetId,
            ORIGIN: sponsor,
            'agent': agent,
            DATA: data}



# TODO: Move them to a separate file
# ROLE types
STEWARD = "STEWARD"


def storedTxn(txnTyp, nym, txnId, role=None, data=None):
    return {
        "type": txnTyp,
        "nym": nym,
        "role": role,
        "data": data,
        "txnId": txnId
    }


def getGenesisTxns():
    return [storedTxn(ADD_NYM,
                    "a3716a7674d089456c603adb5575800bc2d4988e00bc297be7e595de2de61150",
                    "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b",
                    role=STEWARD),
            ]
