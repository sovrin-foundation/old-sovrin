import pytest
from ledger.compact_merkle_tree import CompactMerkleTree
from ledger.ledger import Ledger
from ledger.serializers.compact_serializer import CompactSerializer

from plenum.client.signer import SimpleSigner
from plenum.common.plugin_helper import loadPlugins
from plenum.common.txn_util import createGenesisTxnFile
from plenum.test.plugin.helper import getPluginPath
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.plugin_helper import writeAnonCredPlugin

from sovrin.common.txn import TXN_TYPE, TARGET_NYM, TXN_ID, ROLE, \
    getTxnOrderedFields
from sovrin.common.txn import STEWARD, NYM, SPONSOR
from sovrin.test.cli.helper import newCLI
from sovrin.test.helper import TestNodeSet,\
    genTestClient, createNym, addUser, TestNode, makePendingTxnsRequest
from sovrin.common.util import getConfig

from plenum.test.conftest import getValueFromModule

# noinspection PyUnresolvedReferences
from plenum.test.conftest import tdir, looper, counter, unstartedLooper, \
    nodeReg, up, ready, keySharedNodes, whitelist, logcapture, tconf, \
    tdirWithDomainTxns, txnPoolNodeSet, poolTxnData, dirName, poolTxnNodeNames,\
    allPluginsPath, tdirWithNodeKeepInited, tdirWithPoolTxns


@pytest.fixture(scope="module", autouse=True)
def anonCredPluginFileCreated(tdir):
    writeAnonCredPlugin(tdir, reloadTestModules=True)
    loadPlugins(tdir)


@pytest.fixture(scope="module")
def allPluginsPath():
    return [getPluginPath('stats_consumer')]


@pytest.fixture(scope="module")
def stewardWallet():
    wallet = Wallet('steward')
    seed = b'is a pit   seed, or somepin else'
    wallet.addSigner(seed=seed)
    assert wallet.defaultId == 'LRtO/oin94hzKKCVG4GOG1eMuH7uVMJ3txDUHBX2BqY='
    return wallet


@pytest.fixture(scope="module")
def steward(genned, looper, tdir, up, stewardWallet):
    s, _ = genTestClient(genned, tmpdir=tdir)
    s.registerObserver(stewardWallet.handleIncomingReply)
    looper.add(s)
    looper.run(s.ensureConnectedToNodes())
    return s


@pytest.fixture(scope="module")
def updatedSteward(steward, stewardWallet):
    makePendingTxnsRequest(steward, stewardWallet)


@pytest.fixture(scope="module")
def genesisTxns(stewardWallet: Wallet):
    nym = stewardWallet.defaultId
    return [{
        TXN_TYPE: NYM,
        TARGET_NYM: nym,
        TXN_ID: "9c86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b",
        ROLE: STEWARD
    },]


@pytest.fixture(scope="module")
def domainTxnOrderedFields():
    return getTxnOrderedFields()


@pytest.fixture(scope="module")
def gennedTdir(genesisTxns, tdir, domainTxnOrderedFields):
    config = getConfig(tdir)
    createGenesisTxnFile(genesisTxns, tdir, config.domainTransactionsFile,
                         domainTxnOrderedFields)
    return tdir


@pytest.yield_fixture(scope="module")
def nodeSet(request, tdir, nodeReg, allPluginsPath):

    primaryDecider = getValueFromModule(request, "PrimaryDecider", None)
    with TestNodeSet(nodeReg=nodeReg, tmpdir=tdir,
                     primaryDecider=primaryDecider,
                     pluginPaths=allPluginsPath) as ns:
        yield ns


@pytest.fixture(scope="module")
def genned(gennedTdir, nodeSet):
    return nodeSet


@pytest.fixture(scope="module")
def conf(tdir):
    return getConfig(tdir)


@pytest.fixture(scope="module")
def testNodeClass():
    return TestNode


@pytest.fixture(scope="module")
def updatedDomainTxnFile(tdir, tdirWithDomainTxns, genesisTxns,
                         domainTxnOrderedFields, tconf):
    ledger = Ledger(CompactMerkleTree(),
                    dataDir=tdir,
                    serializer=CompactSerializer(fields=domainTxnOrderedFields),
                    fileName=tconf.domainTransactionsFile)
    for txn in genesisTxns:
        ledger.add(txn)


@pytest.fixture(scope="module")
def gennedTxnPoolNodeSet(updatedDomainTxnFile, txnPoolNodeSet):
    return txnPoolNodeSet


@pytest.fixture(scope="module")
def startedNodes(nodeSet, looper):
    for n in nodeSet:
        n.start(looper.loop)
    return nodeSet


@pytest.fixture(scope="module")
def client1Signer():
    seed = b'client1Signer secret key........'
    signer = SimpleSigner(seed=seed)
    assert signer.verstr == 'TuIpuBcx6P4S0Ez5LUr3HVpWERVHK56XONixonwcAf4='
    return signer


@pytest.fixture("module")
def sponsorCli(looper, tdir):
    return newCLI(looper, tdir)


@pytest.fixture(scope="module")
def clientAndWallet1(client1Signer, looper, nodeSet, tdir, up):
    client, wallet = genTestClient(nodeSet, tmpdir=tdir)
    wallet = Wallet(client.name)
    wallet.addSigner(signer=client1Signer)
    return client, wallet


@pytest.fixture(scope="module")
def client1(clientAndWallet1, looper):
    client, wallet = clientAndWallet1
    looper.add(client)
    looper.run(client.ensureConnectedToNodes())
    return client


@pytest.fixture(scope="module")
def wallet1(clientAndWallet1):
    return clientAndWallet1[1]


@pytest.fixture(scope="module")
def sponsorWallet():
    wallet = Wallet('sponsor')
    seed = b'sponsors are people too.........'
    wallet.addSigner(seed=seed)
    return wallet


@pytest.fixture(scope="module")
def sponsor(genned, addedSponsor, sponsorWallet, looper, tdir):
    s, _ = genTestClient(genned, tmpdir=tdir)
    s.registerObserver(sponsorWallet.handleIncomingReply)
    looper.add(s)
    looper.run(s.ensureConnectedToNodes())
    makePendingTxnsRequest(s, sponsorWallet)
    return s


@pytest.fixture(scope="module")
def addedSponsor(genned, steward, stewardWallet, looper, sponsorWallet):
    createNym(looper, sponsorWallet.defaultId, steward, stewardWallet, SPONSOR)
    return sponsorWallet


@pytest.fixture(scope="module")
def userWalletA(genned, addedSponsor, sponsorWallet, looper, sponsor):
    return addUser(looper, sponsor, sponsorWallet, 'userA')


@pytest.fixture(scope="module")
def userWalletB(genned, addedSponsor, sponsorWallet, looper, sponsor):
    return addUser(looper, sponsor, sponsorWallet, 'userB')


@pytest.fixture(scope="module")
def userIdA(userWalletA):
    return userWalletA.defaultId


@pytest.fixture(scope="module")
def userIdB(userWalletB):
    return userWalletB.defaultId


@pytest.fixture(scope="module")
def userClientA(genned, userWalletA, looper, tdir):
    u, _ = genTestClient(genned, tmpdir=tdir)
    u.registerObserver(userWalletA.handleIncomingReply)
    looper.add(u)
    looper.run(u.ensureConnectedToNodes())
    makePendingTxnsRequest(u, userWalletA)
    return u

