import pytest
import os
import sovrin.test.cli.test_tutorial as testTutorialMod
import plenum.test.conftest as plenumTestConfMod
import shutil

curDirPath = os.path.dirname(os.path.abspath(__file__))
pathForPoolTxnFile = '/home/rkalaria/.sovrin/pool_transactions_sandbox'


def testSpecificModTest(monkeypatch):

    def testTutorialMonkeyPatching():

        @pytest.fixture(scope="module")
        def mockedFaberAgentPort():
            return "5555"

        @pytest.fixture(scope="module")
        def mockedAcmeAgentPort():
            return "6666"

        @pytest.fixture(scope="module")
        def mockedThriftAgentPort():
            return "7777"

        @pytest.fixture(scope="module")
        def mockedPoolNodesStarted():
            pass

        @pytest.fixture(scope="module")
        def mockedPreRequisite(poolNodesStarted):
            pass

        @pytest.fixture(scope="module")
        def mockedTdirWithPoolTxns(tdir, tconf):
            source = os.path.join(pathForPoolTxnFile)
            target = os.path.join(tdir, tconf.poolTransactionsFile)
            shutil.copy(source, target)
            return tdir

        monkeypatch.setattr(plenumTestConfMod, 'tdirWithPoolTxns',
                            mockedTdirWithPoolTxns)

        monkeypatch.setattr(testTutorialMod, 'poolNodesStarted',
                            mockedPoolNodesStarted)

        monkeypatch.setattr(testTutorialMod, 'preRequisite',
                            mockedPreRequisite)

        import sovrin.test.agent.conftest as sovrinAgentConfMod
        monkeypatch.setattr(sovrinAgentConfMod, 'faberAgentPort',
                            mockedFaberAgentPort)
        monkeypatch.setattr(sovrinAgentConfMod, 'acmeAgentPort',
                            mockedAcmeAgentPort)
        monkeypatch.setattr(sovrinAgentConfMod, 'thriftAgentPort',
                            mockedThriftAgentPort)


    testModulePaths = {
        'cli/test_tutorial.py': testTutorialMonkeyPatching
    }

    exitCodes = {}

    for testModName, testMonkeyPatchFunc in testModulePaths.items():
        testModulePath = os.path.join(curDirPath, '../sovrin/test', testModName)
        testMonkeyPatchFunc()
        exitCodes[testModName] = pytest.main(['-s', testModulePath])

    for testMod, testResult in exitCodes.items():
        assert testResult == 0