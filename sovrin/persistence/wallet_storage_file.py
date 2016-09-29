# DEPRECATED
# import json
# import os
# from typing import Any, Dict
#
# from ledger.stores.directory_store import DirectoryStore
# from ledger.stores.text_file_store import TextFileStore
# from plenum.persistence.wallet_storage_file import WalletStorageFile \
#     as PWalletStorageFile
# from sovrin.client.link import LinkInvitation
#
# from sovrin.persistence.attribute_store_file import AttributeStoreFile
# from sovrin.persistence.credential_def_store_file import CredDefStoreFile
# from sovrin.persistence.wallet_storage import WalletStorage
#
#
# class WalletStorageFile(WalletStorage, PWalletStorageFile):
#     def __init__(self, walletDir: str):
#         PWalletStorageFile.__init__(self, walletDir)
#         attrsDirName = "attributes"
#         credDefDirName = "credential_definitions"
#         credFileName = "credentials"
#         credDefKeys = "credential_definition_keys"
#         masterSecret = "master_secret"
#         linkInvitations = "link_invitations"
#
#         dataDir = self.dataLocation
#
#         self.attrStore = AttributeStoreFile(dataDir, attrsDirName)
#         # type: AttributeStoreFile
#
#         self.credDefStore = CredDefStoreFile(dataDir, credDefDirName)
#         # type: CredDefStoreFile
#
#         self.credStore = TextFileStore(dataDir, credFileName,
#                                        storeContentHash=False)
#         self.credDefKeyStore = TextFileStore(dataDir, credDefKeys,
#                                              storeContentHash=False)
#         self.masterSecretStore = TextFileStore(dataDir, masterSecret,
#                                         isLineNoKey = True,
#                                         storeContentHash=False)
#
#         self.linkInvitationStore = DirectoryStore(dataDir, linkInvitations)
#
#
#     def addAttribute(self, name: str, val: Any, origin: str, dest: str = None,
#                      encKey: str = None, encType: str = None,
#                      hashed: bool = False):
#         self.attrStore.addAttribute(name, val, origin, dest, encKey, encType,
#                                     hashed)
#
#     def getAttribute(self, name: str, dest: str = None):
#         return self.attrStore.getAttribute(name, dest)
#
#     @property
#     def attributes(self):
#         return self.attrStore.attributes
#
#     def addCredDef(self, name: str, version: str, dest: str, type: str, ip: str,
#                    port: int, keys: Dict):
#         self.credDefStore.addCredDef(name, version, dest, type, ip, port, keys)
#
#     def getCredDef(self, name: str, version: str, dest: str = None):
#         return self.credDefStore.getCredDef(name, version, dest)
#
#     def addCredential(self, name: str, data: Dict):
#         self.credStore.put(key=name, value=json.dumps(data))
#
#     def getCredential(self, name: str):
#         return self.credStore.get(name)
#
#     @property
#     def credNames(self):
#         keys = []
#         for k, v in self.credStore.iterator():
#             keys.append(k)
#         return keys
#
#     @staticmethod
#     def credDefKeyStoreKey(name, version):
#         return "{},{}".format(name, version)
#
#     def addCredDefSk(self, name: str, version: str, secretKey):
#         key = self.credDefKeyStoreKey(name, version)
#         self.credDefKeyStore.put(key=key, value=secretKey)
#
#     def getCredDefSk(self, name: str, version: str):
#         key = self.credDefKeyStoreKey(name, version)
#         return self.credDefKeyStore.get(key)
#
#     def addMasterSecret(self, masterSecret):
#         self.masterSecretStore.put(value=masterSecret)
#
#     def addLinkInvitation(self, linkInvitation):
#         self.linkInvitationStore.put(key=linkInvitation.name,
#                                      value=json.dumps(
#                                          linkInvitation.getDictToBeStored()))
#
#     def getMatchingLinkInvitations(self, name: str):
#         allMatched = []
#         for k, v in self.linkInvitationStore.iterator():
#             if name == k or name.lower() in k.lower():
#                 liValues = json.loads(v)
#                 li = LinkInvitation.getFromDict(k, liValues)
#                 allMatched.append(li)
#         return allMatched
#
#     @property
#     def masterSecret(self):
#         # Getting the first line of the file, so using key `1`
#         return self.masterSecretStore.get("1")
