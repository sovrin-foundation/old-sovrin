from sovrin.common.txn import TXN_TYPE, TARGET_NYM, ROLE, DATA, TXN_ID, ADD_NYM,\
    STEWARD

STEWARD_SEED = b'steward seed used for signer....'

GENESIS_TRANSACTIONS = [{
    TXN_TYPE: ADD_NYM,
    TARGET_NYM: 'bx3ePPiBdRywm16OOmZdtlzF5FGmX06Fj2sAYbMdF18=',
    TXN_ID: '6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b',
    ROLE: STEWARD,
    DATA: None
}, ]
