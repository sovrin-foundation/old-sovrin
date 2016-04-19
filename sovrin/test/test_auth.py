import asyncio

from plenum.client.signer import SimpleSigner
from plenum.common.types import Reply
from sovrin.common.txn import ADD_NYM, STEWARD
from sovrin.common.txn import storedTxn
from sovrin.persistence.memory_chain_store import MemoryChainStore
from sovrin.server.client_authn import TxnBasedAuthNr


def testAuth():
    pass
    #
    # txn = storedTxn(
    #     ADD_NYM,
    #     "aXMgYSBwaXQgYSBzZWVkLCBvciBzb21lcGluIGVsc2U=",
    #     "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b",
    #     role=STEWARD)
    #
    # loop = asyncio.get_event_loop()
    #
    # sig = SimpleSigner(seed=b'is a pit a seed, or somepin else')
    # store = MemoryChainStore()
    # authNr = TxnBasedAuthNr(store)
    #
    # coro = store.append("", Reply(0, 0, txn), txn["txnId"])
    #
    # loop.run_until_complete(coro)
    #
    # print(sig.verstr)
    #
    # loop.close()
