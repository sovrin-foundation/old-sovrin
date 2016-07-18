import os

from sovrin.test.helper import TestNode, TestClient

from plenum.test.cli.helper import TestCliCore, newCLI as newPlenumCLI
from plenum.test.testable import Spyable
from plenum.common.txn import TARGET_NYM, ROLE
from sovrin.cli.cli import SovrinCli


@Spyable(methods=[SovrinCli.print, SovrinCli.printTokens])
class TestCLI(SovrinCli, TestCliCore):
    pass


def newCLI(nodeRegsForCLI, looper, tdir, subDirectory=None):
    tempDir = os.path.join(tdir, subDirectory) if subDirectory else tdir
    return newPlenumCLI(nodeRegsForCLI, looper, tempDir, cliClass=TestCLI,
                        nodeClass=TestNode, clientClass=TestClient)


def sendNym(cli, nym, role):
    cli.enterCmd("send NYM {}={} "
                 "{}={}".format(TARGET_NYM, nym,
                                ROLE, role))


def checkGetNym(cli, nym):
    cli.enterCmd("send GET_NYM {dest}={nym}".format(dest=TARGET_NYM, nym=nym))
    printeds = ["Getting nym {}".format(nym), "dest id is {}".format(nym),
                "Reply got from nym"]
    assert all(x in cli.lastCmdOutput for x in printeds)
