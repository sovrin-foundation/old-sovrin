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
    printeds = ["Getting nym {}".format(nym), "Transaction id for NYM {} is ".format(nym)]
    checks = [x in cli.lastCmdOutput for x in printeds]
    assert all(checks)
    # TODO: These give NameError, don't know why
    # assert all([x in cli.lastCmdOutput for x in printeds])
    # assert all(x in cli.lastCmdOutput for x in printeds)


def chkNymAddedOutput(cli, nym):
    checks = [x['msg'] == "Nym {} added".format(nym) for x in cli.printeds]
    assert any(checks)
