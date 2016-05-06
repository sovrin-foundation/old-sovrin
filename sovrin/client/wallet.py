from collections import deque
from typing import Dict, Any, Union
from typing import List
from typing import NamedTuple, Optional

import base58
import jsonpickle
from libnacl import crypto_secretbox, crypto_secretbox_open, randombytes, \
    crypto_secretbox_NONCEBYTES, crypto_hash_sha256
from plenum.client.client import Client, ClientProvider
from plenum.client.signer import SimpleSigner
from plenum.common.util import error
from raet.nacling import PrivateKey, SignedMessage, SigningKey, Signer
from sovrin.common.util import getSymmetricallyEncryptedVal

from sovrin.common.txn import ADD_ATTR, ADD_SPONSOR, TXN_TYPE, ADD_AGENT, \
    newTxn, ORIGIN

ENCODING = "utf-8"

TxnVector = NamedTuple("TxnVector", [
    ("id", str),
    ("key", Optional[bytes])])

# TODO: Think of a better name for `b58`
# Cryptonym = NamedTuple("Cryptonym", [("b58", str), ("privateKey", Privateer),
# ("publicKey", Publican)])


# Will need this when presenting attributes to users build from the wallet's
# completed transaction list
class Attribute:
    def __init__(self, name: str, value: str, *txns: TxnVector):
        self.name = name
        self.value = value
        self.txns = list(txns)


class EncryptedWallet:
    def __init__(self, raw: bytes, nonce: bytes):
        self.raw = raw
        self.nonce = nonce

    def decrypt(self, key) -> 'Wallet':
        return Wallet.decrypt(self, key)


Cryptonym = str


# TODO implement a stronger hierarchical deterministic key generation algorithm,
# TODO     like the one discussed here:
# TODO     hierarchical-deterministic-bitcoin-wallets-that-tolerate-key-leakage--short
# TODO     the current implementation should be considered insecure until further
# TODO     analysis is done.
# TODO might want to use the name Keychain instead of Wallet


# TODO use SimpleSigner in wallet
# class SimpleSigner(Signer):
#     def __init__(self, identifier, seed=None):


class Wallet:
    clientNotPresentMsg = "The wallet does not have a client associated with it"

    def __init__(self, client: Union[Client, ClientProvider]=None, rootSeed=None):
        self._rootSeed = rootSeed       # type: PrivateKey
        self.i = 0                      # type: int
        # TODO Need to support multi value attributes, like multiple emails,
        # phone numbers etc.
        # TODO Probably need to know from which sponsor the attributes came from?
        self.attributeEncKeys = {}              # type: Dict[str, str]
        self.pendingTxns = deque()              # type: deque[Dict[str, Any]]
        self.client = client                    # type: Client
        self.completedTxns = []                 # type: List[Dict[str, Any]]
        self.signers = {}
        if self.client:
            self.client.signers = self.signers
            self.client.defaultIdentifier = None

        # TODO this is a bit messy; it steps on top of client's signers. Also,
            # the default SimpleSigner doesn't need to be created.

    @staticmethod
    def decrypt(ec: EncryptedWallet, key: bytes) -> 'Wallet':
        decryped = crypto_secretbox_open(ec.raw, ec.nonce, key)
        decoded = decryped.decode(ENCODING)
        wallet = jsonpickle.decode(decoded)
        # TODO May need to store a version number in the serialized wallet,
        # so we can convert it to a new wallet schema later
        return wallet

    def encrypt(self, key: bytes, nonce: Optional[bytes]=None) -> EncryptedWallet:
        serialized = jsonpickle.encode(self)
        byts = serialized.encode(ENCODING)
        nonce = nonce if nonce else randombytes(crypto_secretbox_NONCEBYTES)
        raw = crypto_secretbox(byts, nonce, key)
        return EncryptedWallet(raw, nonce)

    # TODO Should this also move to the user wallet? Or would the agent have
    # attributes too?
    # TODO Find a better way of adding an attribute and managing keys
    def addAttribute(self,
                     name: str,
                     val: Any,
                     origin: Cryptonym,
                     target: Cryptonym,
                     commit: bool=False):
        # TODO val needs to be serialized first
        encVal, sKey = getSymmetricallyEncryptedVal(val)
        txnData = newTxn(txnType=ADD_ATTR,
                         origin=origin,
                         target=target,
                         data=encVal)
        # TODO Need to sign the transaction

        req = self.addNewTxn(txnData, commit)
        self.attributeEncKeys[name] = sKey
        if req:
            return req

    # TODO Remove the limitation of sharing only those attributes that are there
    #  on the blockchain
    def shareAttribute(self, name: str, shareWith: Cryptonym, commit: bool=False):
        # Getting the attribute only if its already on the blockcahin
        attr = self.getAttribute(name, synced=True)
        if not attr:
            error("Attribute not yet on the blockchain")
        txnId = attr['txnId']
        secretKey = attr['secretKey']
        encTxnId, sKey = getSymmetricallyEncryptedVal(txnId)
        encSecretKey, sKey = getSymmetricallyEncryptedVal(secretKey, secretKey=sKey)

        # TODO: Need to sign this with sponsor's signing key
        signedSKey = sKey

        # TODO Do we need to know add agent and sponsor info here?
        txnData = {
            'txnType': "SHARE_ATTR",
            'targetId': shareWith,
            'data': {
                "txnId": encTxnId,
                "secretKey": encSecretKey,
                "signedKey": signedSKey
            }
        }

        self.addNewTxn(txnData, commit)
        self.attributeEncKeys[name] = sKey

    def newCryptonym(self):
        nym = self._generateCryptonym(self.i + 1)
        self.i += 1
        return nym

    def lastCryptonym(self):
        return self._generateCryptonym(self.i)

    def _generateCryptonym(self, i) -> Cryptonym:
        # TODO need to clear system memory of private keys, including the newly
        # generated private key
        # TODO Need to have a wallet locking mechanism. Can't keep the wallet
        # unlocked for long periods of time.
        # TODO Double locking mechanism? Like one key for general purpose, and
        # another for accessing private keys?
        # TODO Perhaps an encrypted wallet could show the names of attributes,
        # and how many attributes, and if any are pending
        ss = SimpleSigner(identifier=None, seed=self._getKey(i))
        nym = ss.verstr
        ss._identifier = nym
        # TODO this is weird; do we need to store the identifier in SimpleSigner
        #  itself?
        self.signers[nym] = ss
        return nym

    def _getKey(self, i):
        self._checkRootPrivKeyIsSetup()
        newKey = \
            crypto_hash_sha256(
                crypto_hash_sha256(
                    "{}:{}".format(i, base58.b58encode(self._rootSeed))
                )
            )
        # TODO we know this is not the standard algorithm for heirarchical deterministic keys; need to determine the best approach
        return newKey

    def _checkRootPrivKeyIsSetup(self):
        if self._rootSeed is None:
            self._rootSeed = randombytes(32)

    def signMessage(self, msg: Any, i: int=None) -> SignedMessage:
        signer = self.signers[i if i is not None else self.i]
        sig = signer.sign(msg.__dict__)
        return sig

    def processPendingTxnQueue(self):
        txnRequests = []
        out = []
        while self.pendingTxns:
            txnData = self.pendingTxns.popleft()
            txnRequests.append(txnData)

        for txnData in txnRequests:
            req = self.processTxn(txnData)
            out.append(req)
        return out

    def processTxn(self, txnData: Dict[str, Any]):
        # Only when the attempt is made to post a transaction to the blockchain
        # and the wallet does not have a client, an error is raised.
        if self.client is None:
            error(self.clientNotPresentMsg)
        request = self.client.submit(txnData, txnData[ORIGIN])[0]
        return request

    def addNewTxn(self, txnData: Any, commit: bool=False):
        if commit:
            return self.processTxn(txnData)
        else:
            self.pendingTxns.append(txnData)

    def addCompletedTxn(self, txnData: Any):
        self.completedTxns.append(txnData)

    def hasAttribute(self, attrName: str, synced: Optional[bool]=None) -> bool:
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
        # txnCollection = self.completedTxns if synced else self.pendingTxns if synced is not None \
        #     else list(self.pendingTxns) + self.completedTxns
        #
        # for txn in txnCollection:
        #     if txn['txnType'] == "ADD_ATTR":
        #         if isinstance(txn['data'], dict) and attrName in txn['data']:
        #             return True

        return self.getAttribute(attrName, synced) is not None

    # TODO decide between jsonpickle.dumps and json.dumps; would like to just use jsonpickle.dumps

    def getAttribute(self, attrName: str, synced: Optional[bool]=None) -> Optional[Dict[str, Any]]:
        txnCollection = self.completedTxns if synced else self.pendingTxns if synced is not None \
            else list(self.pendingTxns) + self.completedTxns

        for txn in txnCollection:
            if txn[TXN_TYPE] == ADD_ATTR:
                if isinstance(txn['data'], dict) and attrName in txn['data']:
                    return txn

        return None


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
