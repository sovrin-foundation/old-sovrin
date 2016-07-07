import pytest

from plenum.common.looper import Looper
import plenum
from sovrin.common.util import getConfig

plenum.common.util.loggingConfigured = False

from sovrin.test.cli.helper import TestCli, newCli

config = getConfig()


@pytest.yield_fixture(scope="module")
def looper():
    with Looper(debug=False) as l:
        yield l


@pytest.fixture("module")
def cli(nodeRegsForCLI, looper, tdir):
    return newCli(nodeRegsForCLI, looper, tdir)


