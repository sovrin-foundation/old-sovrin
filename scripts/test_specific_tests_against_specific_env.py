#! /usr/bin/env python3

import pytest
import os
import sovrin.test.cli.test_tutorial as testTutorialMod
import plenum.test.conftest as plenumTestConfMod
import shutil

# curDirPath = os.path.dirname(os.path.abspath(__file__))
# pathForPoolTxnFile = '/home/rkalaria/.sovrin/pool_transactions_sandbox'


# default/common monkeypatching required for any env
# def performDefaultMonkeyPatching(config, monkeypatch):
#
#     @pytest.fixture(scope="module")
#     def mockedAgentIpAddress():
#         return config.get("agentIpAddress")
#
#     @pytest.fixture(scope="module")
#     def mockedFaberAgentPort():
#         return config.get("faberAgentPort")
#
#     @pytest.fixture(scope="module")
#     def mockedAcmeAgentPort():
#         return config.get("acmeAgentPort")
#
#     @pytest.fixture(scope="module")
#     def mockedThriftAgentPort():
#         return config.get("thriftAgentPort")
#
#     @pytest.fixture(scope="module")
#     def mockedPoolNodesStarted():
#         pass
#
#     @pytest.fixture(scope="module")
#     def mockedPreRequisite(poolNodesStarted):
#         pass
#
#     @pytest.fixture(scope="module")
#     def mockedTdirWithPoolTxns(tdir, tconf):
#         source = os.path.join(config.get("poolTxnFilePath"))
#         target = os.path.join(tdir, tconf.poolTransactionsFile)
#         os.mkdir(tdir)
#         shutil.copy(source, target)
#         return tdir
#
#     monkeypatch.setattr(plenumTestConfMod, 'tdirWithPoolTxns',
#                         mockedTdirWithPoolTxns)
#
#     monkeypatch.setattr(testTutorialMod, 'poolNodesStarted',
#                         mockedPoolNodesStarted)
#
#     monkeypatch.setattr(testTutorialMod, 'preRequisite',
#                         mockedPreRequisite)
#
#     import sovrin.test.agent.conftest as sovrinAgentConfMod
#     monkeypatch.setattr(sovrinAgentConfMod, 'agentIpAddress',
#                         mockedAgentIpAddress)
#     monkeypatch.setattr(sovrinAgentConfMod, 'faberAgentPort',
#                         mockedFaberAgentPort)
#     monkeypatch.setattr(sovrinAgentConfMod, 'acmeAgentPort',
#                         mockedAcmeAgentPort)
#     monkeypatch.setattr(sovrinAgentConfMod, 'thriftAgentPort',
#                         mockedThriftAgentPort)
#
#
# # define test specific monkey patching
# def tutorialMonkeyPatching(config, monkeypatch):
#     pass
#
#
# # define env specific test config
# sandboxConfig = {
#     "poolTxnFilePath": "/home/rkalaria/.sovrin/pool_transactions_sandbox",
#     "testModulePaths": {
#         'cli/test_tutorial.py': tutorialMonkeyPatching
#     },
#     "agentIpAddress": "54.70.102.199",
#     "faberAgentPort": "5555",
#     "acmeAgentPort": "6666",
#     "thriftAgentPort": "7777",
# }
#
#
# # add all different env configs to this one config against which
# # you want to run specific tests
# envConfigs = {
#     "sandbox": sandboxConfig
# }

# TODO: Need to properly test this and make sure monkey patching
# doesn't break any other tests (which run after this one)

# def testSpecificModTest(monkeypatch):
#     envExitCodes = {}
#     curDirPath = os.path.dirname(os.path.abspath(__file__))
#
#     for ename, econf in envConfigs.items():
#         testModulePaths = econf.get("testModulePaths")
#         performDefaultMonkeyPatching(econf, monkeypatch)
#         exitCodes = {}
#         for testModName, testMonkeyPatchFunc in testModulePaths.items():
#             testModulePath = os.path.join(
#                 curDirPath, '../sovrin/test', testModName)
#             if testMonkeyPatchFunc:
#                 testMonkeyPatchFunc(econf, monkeypatch)
#             exitCodes[testModName] = pytest.main(['-s', testModulePath])
#
#         envExitCodes[ename] = exitCodes
#
#     for ename, exitCodes in envExitCodes.items():
#         for testMod, testResult in exitCodes.items():
#             assert testResult == 0
