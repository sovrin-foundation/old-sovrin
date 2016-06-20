from typing import Any
from typing import Optional

from plenum.client.wallet import Wallet as PWallet
from sovrin.common.txn import ADD_SPONSOR, ADD_AGENT, \
    newTxn
from sovrin.persistence.wallet_storage import WalletStorage

ENCODING = "utf-8"

Cryptonym = str


class Wallet(PWallet):
    clientNotPresentMsg = "The wallet does not have a client associated with it"

    def __init__(self, storage: WalletStorage):
        PWallet.__init__(self, storage=storage)
        # self.attributes = {}
        # self.credDefs = {}

    def addAttribute(self,
                     name: str,
                     val: Any,
                     origin: str,
                     dest: Optional[str]=None,
                     encKey: Optional[str]=None,
                     encType: Optional[str] = None,
                     hashed: bool = False):
        # self.attributes[(name, dest)] = (val, encKey, encType, hashed)
        self.storage.addAttribute(name, val, origin, dest, encKey, encType,
                                  hashed)

    def hasAttribute(self, name: str, dest: Optional[str]=None) -> bool:
        """
        Checks if attribute is present in the wallet
        @param attrName: Name of the attribute
        @param synced: If true then checks whether the transaction for the
        attribute has been written to the blockchain. Looks in the
        `completedTxns` list and returns True if found. If false then checks
        whether the transaction for the attribute has not been written to the
        blockchain. Looks in the `pendingTxns` list and returns True if found
        If None then checks in both `pendingTxns` and `completedTxns` and if
        found in either return true
        @return:
        """
        return bool(self.getAttribute(name, dest))

    def getAttribute(self, name: str, dest: Optional[str]=None):
        return self.storage.getAttribute(name, dest)

    @property
    def attributes(self):
        return self.storage.attributes


class UserWallet(Wallet):
    def add(self, txnType: str, userNym: Cryptonym, sponsorNym: Cryptonym=None, agentNym: Cryptonym=None, commit: bool=False):
        txnData = newTxn(txnType=txnType,
                      targetNym=userNym,
                      sponsor=sponsorNym,
                      agent=agentNym)
        self.addNewTxn(txnData, commit)
        return txnData

    def addSponsor(self, *args, **kwargs):
        self.add(ADD_SPONSOR, *args, **kwargs)

    # User can have agent without having any sponsor
    def addAgent(self, *args, **kwargs):
        self.add(ADD_AGENT, *args, **kwargs)
