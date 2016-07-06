from plenum.common.types import f
from sovrin.common.txn import TXN_TYPE, TARGET_NYM, ROLE, DATA, TXN_ID, NYM,\
    STEWARD, ORIGIN, SPONSOR

STEWARD_SEED = b'steward seed used for signer....'

GENESIS_TRANSACTIONS = [
    {
        TXN_TYPE: NYM,
        TARGET_NYM: 'OP2h59vBVQerRi6FjoOoMhSTv4CAemeEg4LPtDHaEWw=',
        TXN_ID: '6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b',
        ROLE: STEWARD
    },
    {
        TXN_TYPE: NYM,
        f.IDENTIFIER.nm: 'OP2h59vBVQerRi6FjoOoMhSTv4CAemeEg4LPtDHaEWw=',
        TARGET_NYM: 'MnT3cFlVvVu7QO+QzPp5seU14pkOT7go1PsqDWZSrbo=',
        ROLE: SPONSOR,
        TXN_ID: '6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4c'
    },
    # {
    #     TXN_TYPE: NYM,
    #     f.IDENTIFIER.nm: 'OP2h59vBVQerRi6FjoOoMhSTv4CAemeEg4LPtDHaEWw=',
    #     TARGET_NYM: 'ARyM91PzDKveCuqkV9B6TJ5f9YxI8Aw/cz5eDAduNUs=',
    #     ROLE: SPONSOR,
    #     TXN_ID: '6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4d'
    # }
]
