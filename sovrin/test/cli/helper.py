from sovrin.test.helper import TestNode, TestClient

from plenum.test.cli.helper import TestCliCore, newCLI as newPlenumCLI
from plenum.test.testable import Spyable
from sovrin.cli.cli import SovrinCli


@Spyable(methods=[SovrinCli.print, SovrinCli.printTokens])
class TestCli(SovrinCli, TestCliCore):
    pass


def newCli(nodeRegsForCLI, looper, tdir):
    return newPlenumCLI(nodeRegsForCLI, looper, tdir, cliClass=TestCli,
                        nodeClass=TestNode, clientClass=TestClient)
