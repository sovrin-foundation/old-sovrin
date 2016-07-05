from plenum.test.cli.helper import TestCliCore
from plenum.test.testable import Spyable
from sovrin.cli.cli import SovrinCli


@Spyable(methods=[SovrinCli.print, SovrinCli.printTokens])
class TestCli(SovrinCli, TestCliCore):
    pass
