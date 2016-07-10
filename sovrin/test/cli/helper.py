import os

from sovrin.test.helper import TestNode, TestClient

from plenum.test.cli.helper import TestCliCore, newCLI as newCLIP
from plenum.test.testable import Spyable
from plenum.common.txn import TARGET_NYM, ROLE
from sovrin.cli.cli import SovrinCli
from plenum.cli.cli import Cli as PlenumCLI


@Spyable(methods=[SovrinCli.print, SovrinCli.printTokens])
class TestCLI(SovrinCli, TestCliCore):
    pass


def newCLI(nodeRegsForCLI, looper, tdir, subDirectory=None):
    tempDir = os.path.join(tdir, subDirectory) if subDirectory else tdir
    return newCLIP(nodeRegsForCLI, looper, tempDir, cliClass=TestCLI,
                   nodeClass=TestNode, clientClass=TestClient)


def sendNym(cli, nym, role):
    cli.enterCmd("send NYM {}={} "
                 "{}={}".format(TARGET_NYM, nym,
                                ROLE, role))
