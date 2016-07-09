from sovrin.test.helper import TestNode, TestClient

from plenum.test.cli.helper import TestCliCore, newCLI as newPlenumCLI
from plenum.test.testable import Spyable
from plenum.common.txn import TARGET_NYM, ROLE
from sovrin.cli.cli import SovrinCli
from plenum.cli.cli import Cli as PlenumCLI


@Spyable(methods=[SovrinCli.print, SovrinCli.printTokens])
class TestCLI(SovrinCli, TestCliCore):

    def newClient(self, clientName, seed=None, identifier=None, signer=None):
        return PlenumCLI.newClient(self, clientName, seed, identifier, signer)


def newCLI(nodeRegsForCLI, looper, tdir):
    return newPlenumCLI(nodeRegsForCLI, looper, tdir, cliClass=TestCLI,
                        nodeClass=TestNode, clientClass=TestClient)


def sendNym(cli, nym, role):
    cli.enterCmd("send NYM {}={} "
                 "{}={}".format(TARGET_NYM, nym,
                                ROLE, role))
