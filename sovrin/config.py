import os
from collections import OrderedDict

from plenum.common.txn import ClientBootStrategy

nodeReg = OrderedDict([
    ('Alpha', ('127.0.0.1', 9701)),
    ('Beta', ('127.0.0.1', 9703)),
    ('Gamma', ('127.0.0.1', 9705)),
    ('Delta', ('127.0.0.1', 9707))
])

cliNodeReg = OrderedDict([
    ('AlphaC', ('127.0.0.1', 9702)),
    ('BetaC', ('127.0.0.1', 9704)),
    ('GammaC', ('127.0.0.1', 9706)),
    ('DeltaC', ('127.0.0.1', 9708))
])

baseDir = "~/.sovrin"

# TODO: Rename `transactions_sandbox` to `domain_transactions_sandbox`
domainTransactionsFile = "transactions_sandbox"
poolTransactionsFile = "pool_transactions_sandbox"

logFilePath = "cli.log"

outFilePath = "cli_output.log"

clientBootStrategy = ClientBootStrategy.Custom

hashStore = {
    "type": "orientdb"
}

primaryStorage = None

secondaryStorage = None

OrientDB = {
    "user": "sovrin",
    "password": "password",
    "host": "127.0.0.1",
    "port": 2424
}

'''
Client has the identity graph or not. True will make the client have
identity graph and False will make client not have it

Possible values: True|False

If True, then OrientDB is required.
'''
ClientIdentityGraph = False

'''
The storage type clients use to store requests and replies. Possible values
are file and OrientDB.

Possible values: "orientdb"|"file"
'''
ReqReplyStore = "file"

RAETLogLevel = "concise"
RAETLogLevelCli = "mute"
RAETLogFilePath = os.path.join(os.path.expanduser(baseDir), "raet.log")
RAETLogFilePathCli = None
RAETMessageTimeout = 30


PluginsToLoad = []
