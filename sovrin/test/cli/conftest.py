import os

import pytest

from plenum.common.looper import Looper
from plenum.test.cli.mock_output import MockOutput
from plenum.test.cli.conftest import nodeRegsForCLI
import plenum
from sovrin.common.util import getConfig

plenum.common.util.loggingConfigured = False

from sovrin.test.cli.helper import TestCli
from sovrin.test.helper import TestNode, TestClient


config = getConfig()


@pytest.yield_fixture(scope="module")
def looper():
    with Looper(debug=False) as l:
        yield l


@pytest.fixture("module")
def cli(nodeRegsForCLI, looper, tdir):
    mockOutput = MockOutput()
    curDir = os.getcwd()
    outFilePath = os.path.join(curDir, config.outFilePath)
    Cli = TestCli(looper=looper,
                  basedirpath=tdir,
                  nodeReg=nodeRegsForCLI.nodeReg,
                  cliNodeReg=nodeRegsForCLI.cliNodeReg,
                  output=mockOutput,
                  outFilePath=outFilePath,
                  debug=True)
    Cli.NodeClass = TestNode
    Cli.ClientClass = TestClient
    Cli.basedirpath = tdir
    return Cli