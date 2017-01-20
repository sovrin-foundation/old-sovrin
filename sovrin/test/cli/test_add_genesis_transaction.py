from plenum.test.cli.helper import checkCmdValid

from sovrin.common.txn import STEWARD, NYM
from sovrin.common.txn import TARGET_NYM, ROLE


def testAddGenesisTransactions(cli):
    nym = "cx3ePPiBdRyab1900mZdtlzF5FGmX06Fj2sAYbMdF18="
    role = STEWARD
    typ = NYM
    checkCmdValid(cli, "add genesis transaction {} dest={} role={}"
                  .format(typ, nym, role))
    nymCorrect = False
    roleCorrect = False

    for txn in cli.genesisTransactions:
        if not nymCorrect and txn.get(TARGET_NYM) == nym:
            nymCorrect = True
            if txn.get(ROLE) == role:
                roleCorrect = True

    assert nymCorrect and roleCorrect
    assert "Genesis transaction added" in cli.lastCmdOutput

