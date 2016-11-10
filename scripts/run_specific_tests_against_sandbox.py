import pytest
import os
import sovrin.test.cli.test_tutorial as testTutorialMod

curDirPath = os.path.dirname(os.path.abspath(__file__))


def testSpecificModTest(monkeypatch):
    def testTutorialMonkeyPatching():

        @pytest.fixture(scope="module")
        def poolNodesStarted():
            print("##----------------: Mocked poolNodesStarted")

        @pytest.fixture(scope="module")
        def preRequisite():
            print("##----------------: Mocked preRequisite")

        monkeypatch.setattr(testTutorialMod, 'poolNodesStarted',
                            poolNodesStarted)
        monkeypatch.setattr(testTutorialMod, 'preRequisite', preRequisite)


    testModulePaths = {
        'cli/test_tutorial.py': testTutorialMonkeyPatching
    }

    exitCodes = {}

    for testModName, testMonkeyPatchFunc in testModulePaths.items():
        testModulePath = os.path.join(curDirPath, '../sovrin/test', testModName)
        testMonkeyPatchFunc()
        exitCodes[testModName] = pytest.main(['-s', testModulePath])

    print("\nResults for test modules:")
    for k, v in exitCodes.items():
        print('{}: {}'.format(k, v))
