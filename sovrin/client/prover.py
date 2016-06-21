# from typing import Dict, Union, Tuple
#
# from raet.raeting import AutoMode
#
# from plenum.client.signer import Signer
# from plenum.common.has_file_storage import HasFileStorage
# from plenum.common.stacked import SimpleStack
# from plenum.common.types import HA
# from anoncreds.protocol.prover import Prover as ACProver
#
# from sovrin.client import PROVER
# from sovrin.persistence.entity_file_store import EntityFileStore
#
#
# class Prover():
#     def __init__(self):
#         # HasFileStorage.__init__(self, name, baseDir=basedirpath,
#         #                         dataDir=dataDir)
#
#         # self.proverStore = EntityFileStore(name=name,
#         #                                    dataDir=self.getDataLocation())
#
#         self.provers = {}  # Map[ProverNym, Prover]
#         self.issuers = {}  # Map[ProverNym, IssuerNym]
#         self.verifiers = {}
#         self.requests = []
#
#     def addIssuer(self, issuerName: str, issuerHa: HA):
#         if issuerName not in self.issuers:
#             self.issuers[issuerName] = {'ha': issuerHa, 'credential': None}
#             self.peerStack.registry[issuerName] = issuerHa
#             self.peerStack.maintainConnections()
#
#     def addVerifier(self, verifierName: str, verifierHa: HA):
#         if verifierName not in self.verifiers:
#             self.verifiers[verifierName] = {
#                 'ha': verifierHa,
#                 'credential': None
#             }
#             self.peerStack.registry[verifierName] = verifierHa
#             self.peerStack.maintainConnections()
#
#     def sendCredRequest(self):
#         pass
