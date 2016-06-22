import json

from plenum.common.txn import KEYS


def getCredDefTxnData(credDef):
    credDef = credDef.get()
    keys = credDef[KEYS]
    keys["R"].pop("0")
    keys = {
        "master_secret_rand": int(keys.get("master_secret_rand")),
        "N": int(keys.get("N")),
        "S": int(keys.get("S")),
        "Z": int(keys.get("Z")),
        "attributes": {k: int(v) for k, v in keys["R"].items()}
    }
    credDef[KEYS] = json.dumps(keys)
    return credDef
