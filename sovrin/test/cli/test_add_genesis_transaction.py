from plenum.test.cli.helper import checkCmdValid


def testAddGenesisTransactions(cli):
    checkCmdValid(cli, "add genesis transaction NYM dest=cx3ePPiBdRyab1900mZdtlzF5FGmX06Fj2sAYbMdF18= txnId=0b68b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b role=STEWARD")
    txn = {
        "type": "NYM",
        "dest": "cx3ePPiBdRyab1900mZdtlzF5FGmX06Fj2sAYbMdF18=",
        "txnId": "0b68b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b",
        "role": "STEWARD",
    }
    assert txn in cli._genesisTransactions
    assert "Genesis transaction added" in cli.lastCmdOutput

