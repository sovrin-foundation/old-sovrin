# import unittest
# from unittest import TestCase
#
# import libnacl
# import pytest as pytest
# from raet.nacling import Verifier, Signer
#
# from plenum.test.deep_eq import deep_eq
# from sovrin.client.wallet import Wallet
#
#
# @unittest.skip("Wallet implementation changed")
# class TestWallet(TestCase):
#     cmnArgs = dict(target=None, origin=None)
#
#     def test_encryptAndDecrypt(self):
#         with self.subTest("encrypt"):
#             w = Wallet()
#             w.newCryptonym()
#             w.addAttribute(name="name", val="John Bonham", **self.cmnArgs)
#             w.addAttribute(name="hobby", val="drums", **self.cmnArgs)
#             key = self.randomWalletKey()
#             encryptedWallet = w.encrypt(key)
#         with self.subTest("decrypt with wallet"):
#             w2 = Wallet.decrypt(encryptedWallet, key)
#             deep_eq(w, w2)
#         with self.subTest("decrypt with EncryptedWallet"):
#             w3 = encryptedWallet.decrypt(key)
#             deep_eq(w, w3)
#             deep_eq(w2, w3)
#
#     def randomWalletKey(self):
#         return libnacl.randombytes(size=32)
#
#     @pytest.mark.skipif(True, reason="Will be changed once Wallet is refactored")
#     def test_pending(self):
#         w = Wallet()
#         w.addAttribute(name="name", val="Robert Plant", **self.cmnArgs)
#         assert w.hasAttribute("name") == True
#
#     def test_synchronizeWithBlockchain(self):
#         # TODO finish this
#         pass
#
#     def checkValidCryptonym(self, cryptonym):
#         # TODO check input and assert it is correct
#         pass
#
#     def test_generatingWalletWithOneCryptonym(self):
#         w = Wallet()
#         self.assertIsNone(w._rootSeed)
#         self.assertEquals(w.i, 0)
#         crs = []
#         for n in range(5):
#             cr = w.newCryptonym()
#             self.checkValidCryptonym(cr)
#             self.assertEquals(w.i, n+1)
#             self.assertIsNotNone(w._rootSeed)
#             crs.append(cr)
#         return w, crs
#
#     def test_WalletKeysAreDeterministic(self):
#         w, crs = self.test_generatingWalletWithOneCryptonym()
#         key = self.randomWalletKey()
#         ew = w.encrypt(key)
#         w2 = ew.decrypt(key)
#         self.assertEquals(w2.i, len(crs))
#         for i, cr in enumerate(crs):
#             x = w2._generateCryptonym(i + 1)
#             self.assertEquals(x, crs[i])
#
#     # TODO we need to understand if libnacl.public.Box can help us
#
#     def testLibNaclSigning(self):
#         signerBob = Signer()
#         print("Bob Signer keyhex = {0}\n".format(signerBob.keyhex))
#         self.assertEqual(len(signerBob.keyhex), 64)
#         self.assertEqual(len(signerBob.keyraw), 32)
#         print("Bob Signer verhex = {0}\n".format(signerBob.verhex))
#         self.assertEqual(len(signerBob.verhex), 64)
#         self.assertEqual(len(signerBob.verraw), 32)
#
#         # creating verifier from verhex
#         verferPam = Verifier(signerBob.verhex)
#         print("Pam Verifier keyhex = {0}\n".format(verferPam.keyhex))
#         self.assertEqual(len(verferPam.keyhex), 64)
#         self.assertEqual(len(verferPam.keyraw), 32)
#         self.assertEqual(verferPam.keyhex, signerBob.verhex)
#
#         msg = b"Hello This is Bob, how are you Pam?"
#         signature = signerBob.signature(msg)
#         print("Signed by Bob: Msg len={0} '{1}' Sig Len={2}\n".format(
#                  len(msg), msg, len(signature)))
#         self.assertEqual(len(msg), 35)
#         self.assertEqual(len(signature), 64)
#
#         verified = verferPam.verify(signature, msg)
#         self.assertTrue(verified)
#         print("Verified by Pam = {0}\n".format(verified))
#
#         # creating verifier from verraw
#         verferPam = Verifier(signerBob.verraw)
#         print("Pam Verifier keyhex = {0}\n".format(verferPam.keyhex))
#         self.assertEqual(len(verferPam.keyhex), 64)
#         self.assertEqual(len(verferPam.keyraw), 32)
#         self.assertEqual(verferPam.keyhex, signerBob.verhex)
#         verified = verferPam.verify(signature, msg)
#         self.assertTrue(verified)
#         print("Verified by Pam = {0}\n".format(verified))
#
#         # creating verifier from key object
#         verferPam = Verifier(verferPam.key)
#         print("Pam Verifier keyhex = {0}\n".format(verferPam.keyhex))
#         self.assertEqual(len(verferPam.keyhex), 64)
#         self.assertEqual(len(verferPam.keyraw), 32)
#         self.assertEqual(verferPam.keyhex, signerBob.verhex)
#         verified = verferPam.verify(signature, msg)
#         self.assertTrue(verified)
#         print("Verified by Pam = {0}\n".format(verified))
#
#     def test_signingAndVerifyingAMessage(self):
#         pass
#
#     def addAttributeToAWallet(self):
#
#         pass
#
#     def addSponsorToAWallet(self):
#         pass

