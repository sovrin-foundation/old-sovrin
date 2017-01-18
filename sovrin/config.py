import os
from collections import OrderedDict

from plenum.common.txn import ClientBootStrategy
from sovrin.common.constants import Environment

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
configTransactionsFile = "config_transactions"

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

ENVS = {
    "test": Environment("pool_transactions_sandbox", "transactions_sandbox"),
    "live": Environment("pool_transactions_live", "transactions_live")
}

# File that stores the version of the Node ran the last time it started. (It
# might be incorrect sometimes if Node failed to update the file and crashed)
lastRunVersionFile = 'last_version'


# File that stores the version of the code to which the update has to be made.
# This is used to detect if there was an error while upgrading. Once it has
# been found out that there was error while upgrading, then it can be upgraded.
nextVersionFile = 'next_version'


# Minimum time difference (seconds) between the code update of 2 nodes
MinSepBetweenNodeUpgrades = 300
