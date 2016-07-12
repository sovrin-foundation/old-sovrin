from typing import Any, Dict
from typing import Optional

from plenum.client.wallet import Wallet as PWallet
from sovrin.common.txn import ADD_SPONSOR, ADD_AGENT, \
    newTxn
from sovrin.persistence.wallet_storage import WalletStorage

ENCODING = "utf-8"

Cryptonym = str


class Wallet(PWallet):
    clientNotPresentMsg = "The wallet does not have a client associated with it"

    def __init__(self, name: str, storage: WalletStorage):
        PWallet.__init__(self, name, storage=storage)

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

    def addCredDef(self, name: str, version: str, dest: str, typ: str, ip: str,
                   port: int, keys: Dict):
        self.storage.addCredDef(name, version, dest, typ, ip, port, keys)

    def getCredDef(self, name: str, version: str, dest: str = None):
        return self.storage.getCredDef(name, version, dest)

    def addCredDefSk(self, name: str, version: str, secretKey):
        self.storage.addCredDefSk(name, version, secretKey)

    def getCredDefSk(self, name: str, version: str):
        return self.storage.getCredDefSk(name, version)

    def addCredential(self, name: str, data: Dict):
        self.storage.addCredential(name, data)

    def getCredential(self, name: str):
        return self.storage.getCredential(name)

    def addMasterSecret(self, masterSecret):
        self.storage.addMasterSecret(masterSecret)

    # TODO Make a property
    def getMasterSecret(self):
        return self.storage.getMasterSecret()

    @property
    def credNames(self):
        return self.storage.credNames


# class UserWallet(Wallet):
#     def add(self, txnType: str, userNym: Cryptonym, sponsorNym: Cryptonym=None, agentNym: Cryptonym=None, commit: bool=False):
#         txnData = newTxn(txnType=txnType,
#                       targetNym=userNym,
#                       sponsor=sponsorNym,
#                       agent=agentNym)
#         self.addNewTxn(txnData, commit)
#         return txnData
#
#     def addSponsor(self, *args, **kwargs):
#         self.add(ADD_SPONSOR, *args, **kwargs)
#
#     # User can have agent without having any sponsor
#     def addAgent(self, *args, **kwargs):
#         self.add(ADD_AGENT, *args, **kwargs)
