# import json
# from typing import Dict, Union, Tuple
#
# from raet.raeting import AutoMode
#
# from plenum.client.signer import Signer
# from plenum.common.has_file_storage import HasFileStorage
# from plenum.common.stacked import SimpleStack
# from plenum.common.txn import ORIGIN, TARGET_NYM, TXN_TYPE, DATA
# from plenum.common.types import HA
# from anoncreds.protocol.issuer import Issuer as CredDef
#
# from sovrin.client import ISSUER
# from sovrin.common.txn import ADD_PKI
# from sovrin.persistence.entity_file_store import EntityFileStore
#
#
# class Issuer():
#     def __init__(self):
#         # HasFileStorage.__init__(self,
#         #                         name,
#         #                         baseDir=basedirpath,
#         #                         dataDir=dataDir)
#         # self.issuerStore = EntityFileStore(name=name,
#         #                                    dataDir=self.getDataLocation())
#         self.issuers = dict()  # Map[attrNames, Issuer]
#         self.provers = dict()  # Map[ProverNym, ProverHA]
#         self.credentials = dict()  # Map[ProverNym, {credential: <A, e, vprimeprime>, attributesData: <the plain text attribute data>}]
#
#     def hasCredDef(self, attrNames: Tuple[str]) -> bool:
#         return attrNames in self.issuers
#
#     def createCredDef(self, attrNames: Tuple[str]):
#         self.issuers[attrNames] = CredDef(attrNames)
#
#     # def persistIssuer(self, name: str, issuer: Issuer):
#     #     pk = issuer.PK
#     #     R = [v for k, v in sorted(pk['R'].items(), key=lambda x: int(x[0]))]
#     #     issuerData = ",".join([str(n)
#     #                            for n in (issuer.p_prime,
#     #                                      issuer.q_prime,
#     #                                      issuer.p,
#     #                                      issuer.q,
#     #                                      pk['N'],
#     #                                      pk['S'],
#     #                                      pk['Z'],
#     #                                      '|'.join(R), )])
#     #     self.issuerStore.add(name, issuerData)
#
#     # def retrieveIssuer(self, name: str):
#     #     issuerData = self.issuerStore.get(name)
#     #     p_prime, q_prime, p, q, N, S, Z, R = issuerData.split(",")
#     #     R = {str(i + 1): r for i, r, in R.split("|")}
#     #     issuer = Issuer(len(R))
#     #     issuer.p = p
#     #     issuer.q = q
#     #     issuer.p_prime = p_prime
#     #     issuer.q_prime = q_prime
#     #     issuer._pk = {'N': N, 'S': S, 'Z': Z, 'R': R}
#     #     issuer.sk = {'p': p, 'q': q}
#     #     return issuer
#
#     def addProver(self, proverNym, ha):
#         self.provers[proverNym] = ha
#
#     def addPkiToLedger(self, attrNames):
#         attrNames = tuple(sorted(attrNames))
#         if not self.hasIssuer(attrNames):
#             self.createIssuer(attrNames)
#         issuer = self.issuers[attrNames]
#
#         issuerNym = self.sovrinClient.defaultIdentifier
#
#         pk = {
#             "N": int(issuer.PK["N"]),
#             "R": {k: int(v)
#                   for k, v in issuer.PK["R"].items()},
#             "S": int(issuer.PK["S"]),
#             "Z": int(issuer.PK["Z"]),
#         }
#         op = {
#             ORIGIN: issuerNym,
#             TARGET_NYM: issuerNym,
#             TXN_TYPE: ADD_PKI,
#             DATA: json.dumps({
#                 "public_key": pk,
#             })
#         }
#         return self.sovrinClient.submit(op)
#
#     def handlePeerMessage(self, wrappedMsg):
#         msg, frm = wrappedMsg
#         print(wrappedMsg)
