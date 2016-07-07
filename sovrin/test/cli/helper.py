from sovrin.common.txn import NYM
from sovrin.test.helper import TestNode, TestClient

from plenum.test.cli.helper import TestCliCore, newCLI as newPlenumCLI
from plenum.test.testable import Spyable
from plenum.common.txn import TARGET_NYM, TXN_TYPE, ROLE
from sovrin.cli.cli import SovrinCli


@Spyable(methods=[SovrinCli.print, SovrinCli.printTokens])
class TestCli(SovrinCli, TestCliCore):
    pass


def newCli(nodeRegsForCLI, looper, tdir):
    return newPlenumCLI(nodeRegsForCLI, looper, tdir, cliClass=TestCli,
                        nodeClass=TestNode, clientClass=TestClient)


def sendNym(cli, nym, role):
    cli.enterCmd("send NYM {}={} "
                 "{}={}".format(TARGET_NYM, nym,
                                ROLE, role))
