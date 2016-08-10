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

domainTransactionsFile = "transactions"
poolTransactionsFile = "pool_transactions"

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
    "port": 2424,
    "startScript": "/opt/orientdb/bin/server.sh",
    "shutdownScript": "/opt/orientdb/bin/shutdown.sh"
}


RAETLogLevel = "concise"
