import pytest
import re

from plenum.common.looper import Looper
from plenum.common.txn import TARGET_NYM, DATA, NAME, VERSION
from plenum.common.util import getlogger
from plenum.test.eventually import eventually
from plenum.test.cli.conftest import nodeRegsForCLI, createAllNodes, nodeNames
from plenum.test.cli.helper import newKeyPair, checkCmdValid, \
    assertAllNodesCreated, checkAllNodesStarted, checkAllNodesUp, \
    checkClientConnected
from plenum.test.eventually import eventually
from sovrin.test.cli.helper import newCLI
from sovrin.common.txn import SPONSOR, USER, ROLE, CRED_DEF


logger = getlogger()


"""
Test Plan:

6 CLI instances - 1 to run the consensus pool and 4 for clients.
5 clients - Phil, Tyler, BookStore, BYU and Trustee

Phil is a pre-existing sponsor on Sovrin
BYU is a sponsor added by Phil to Sovrin
Tyler is a user added by BYU to Sovrin
BookStore is a user already on Sovrin
Trustee is a generic trustee who will add BookStore's nym.

Plenum Fixtures:
1. For Phil,
Create a sponsor on Sovrin with keypair alias Phil. This should be done on
his CLI, so that when Phil gives a 'list ids' command, he can see his
keypair and the alias.
2. Fixture to add BookStore as a user.
3. BYU does the same operation as Phil, but without alias. (same fixture as
 Phil)
4. Tyler creates a keypair and sends it to BYU. BYU creates the NYM for
Tyler. (2 fixtures)

Sovrin Fixtures:
1. Adding credDef to the ledger.
2.

Optional:
BYU adds a public attribute, mailing address

Out of Band communication:
Passing public keys from user to sponsor: The test case passes the
objects from one cli to another directly.


"""


def addNewKey(*clis):
    for cli in clis:
        cli.enterCmd("new key")
        assert 'Key created in wallet' in cli.lastCmdOutput


def chkNymAddedOutput(cli, nym):
    assert cli.printeds[0]['msg'] == "Nym {} added".format(nym)


def ensureNymAdded(cli, nym, role=USER):
    cli.enterCmd("send NYM {dest}={nym} {ROLE}={role}".format(
        dest=TARGET_NYM, nym=nym, ROLE=ROLE, role=role))
    cli.looper.run(
        eventually(chkNymAddedOutput, cli, nym, retryWait=1,
                   timeout=10))


@pytest.yield_fixture(scope="module")
def poolCLI(nodeRegsForCLI, tdir):
    with Looper(debug=False) as looper:
        yield newCLI(nodeRegsForCLI, looper, tdir, subDirectory="pool")


@pytest.yield_fixture(scope="module")
def byuCLI(nodeRegsForCLI, tdir):
    with Looper(debug=False) as looper:
        yield newCLI(nodeRegsForCLI, looper, tdir, subDirectory="byu")


@pytest.yield_fixture(scope="module")
def philCLI(nodeRegsForCLI, tdir):
    with Looper(debug=False) as looper:
        yield newCLI(nodeRegsForCLI, looper, tdir, subDirectory="phil")


@pytest.yield_fixture(scope="module")
def trusteeCLI(nodeRegsForCLI, tdir):
    with Looper(debug=False) as looper:
        yield newCLI(nodeRegsForCLI, looper, tdir, subDirectory="trustee")


@pytest.yield_fixture(scope="module")
def tylerCLI(nodeRegsForCLI, tdir):
    with Looper(debug=False) as looper:
        yield newCLI(nodeRegsForCLI, looper, tdir, subDirectory="tyler")


@pytest.yield_fixture(scope="module")
def bookStoreCLI(nodeRegsForCLI, tdir):
    with Looper(debug=False) as looper:
        yield newCLI(nodeRegsForCLI, looper, tdir, subDirectory="bookStore")


@pytest.fixture(scope="module")
def poolNodesCreated(poolCLI, nodeNames, philCreated, trusteeCreated):
    createAllNodes(poolCLI)
    assertAllNodesCreated(poolCLI, nodeNames)
    checkAllNodesStarted(poolCLI, *nodeNames)


def testPoolNodesCreated(poolNodesCreated):
    pass


@pytest.fixture(scope="module")
def philPubKey(philCLI):
    return newKeyPair(philCLI)


@pytest.fixture(scope="module")
def trusteePubKey(trusteeCLI):
    return newKeyPair(trusteeCLI)


@pytest.fixture(scope="module")
def bookStoreKey(bookStoreCLI):
    return newKeyPair(bookStoreCLI)


@pytest.fixture(scope="module")
def byuPubKey(byuCLI):
    return newKeyPair(byuCLI)


@pytest.fixture(scope="module")
def tylerPubKey(tylerCLI):
    return newKeyPair(tylerCLI, alias='Tyler')   # or should it be "forBYU"?


@pytest.fixture(scope="module")
def bookStorePubKey(bookStoreCLI):
    return newKeyPair(bookStoreCLI, alias='BookStore')


@pytest.fixture(scope="module")
def philCreated(poolCLI, philPubKey):
    checkCmdValid(poolCLI, "add genesis transaction NYM dest={} role=STEWARD".
                  format(philPubKey))
    assert "Genesis transaction added." in poolCLI.lastCmdOutput


# TODO: Find a better name for `trustee`.
@pytest.fixture(scope="module")
def trusteeCreated(poolCLI, trusteePubKey):
    checkCmdValid(poolCLI, "add genesis transaction NYM dest={} role=STEWARD".
                  format(trusteePubKey))
    assert "Genesis transaction added." in poolCLI.lastCmdOutput


@pytest.fixture(scope="module")
def philConnected(philCreated, philCLI, poolNodesCreated, nodeNames):
    philCLI.looper.run(eventually(checkClientConnected, philCLI, nodeNames,
                                  philCLI.activeClient.name, retryWait=1,
                                  timeout=5))


@pytest.fixture(scope="module")
def trusteeConnected(trusteeCreated, trusteeCLI, poolNodesCreated, nodeNames):
    trusteeCLI.looper.run(eventually(checkClientConnected, trusteeCLI, nodeNames,
                                     trusteeCLI.activeClient.name, retryWait=1,
                                    timeout=5))


@pytest.fixture(scope="module")
def bookStoreCreated(bookStorePubKey, trusteeConnected, trusteeCLI):
    ensureNymAdded(trusteeCLI, bookStorePubKey, USER)


@pytest.fixture(scope="module")
def byuCreated(byuPubKey, philConnected, philCLI):
    ensureNymAdded(philCLI, byuPubKey, SPONSOR)


@pytest.fixture(scope="module")
def byuConnected(byuCreated, byuCLI, poolNodesCreated, nodeNames):
    byuCLI.looper.run(eventually(checkClientConnected, byuCLI, nodeNames,
                                 byuCLI.activeClient.name, retryWait=1,
                                  timeout=5))
    logger.debug("BYU connected")


@pytest.fixture(scope="module")
def tylerCreated(tylerPubKey, byuConnected, byuCLI):
    ensureNymAdded(byuCLI, tylerPubKey, USER)


@pytest.fixture(scope="module")
def tylerConnected(tylerCreated, tylerCLI, poolNodesCreated, nodeNames):
    tylerCLI.looper.run(eventually(checkClientConnected, tylerCLI, nodeNames,
                                   tylerCLI.activeClient.name, retryWait=1,
                                  timeout=5))
    logger.debug("Tyler connected")


#TODO: Remove
@pytest.fixture(scope="module")
def setup(poolCLI, philCLI, bookStoreCLI, byuCLI, tylerCLI):
    # for node in poolCLI.nodes.values():
    #     for cli in [philCLI, bookStoreCLI, byuCLI, tylerCLI]:
    #         node.whitelistClient(cli.defaultClient.name)
    pass


@pytest.fixture(scope="module")
def byuAddsCredDef(byuCLI, byuCreated, tylerCreated, byuPubKey):
    # TODO tylerAdded ensures that activeClient is already set.
    """BYU writes a credential definition to Sovrin."""
    cmd = ("send CRED_DEF name=Degree version=1.0 "
           "type=JC1 ip=10.10.10.10 port=7897 keys=undergrad,last_name,"
           "first_name,birth_date,postgrad,expiry_date")
    checkCmdValid(byuCLI, cmd)

    def checkCredAdded():
        txns = byuCLI.activeClient.getTxnsByType(CRED_DEF)
        assert any(txn[NAME] == 'Degree' and
                   txn[VERSION] == '1.0'
                   for txn in txns)

    byuCLI.looper.run(eventually(checkCredAdded, retryWait=1, timeout=15))
    output = byuCLI.lastCmdOutput
    assert "credential definition is published" in output
    assert "Degree" in output
    return byuCLI.activeSigner.verstr


@pytest.fixture(scope="module")
def attrRepoInitialized(byuCLI, byuCreated):
    assert byuCLI.activeClient.attributeRepo is None
    byuCLI.enterCmd("initialize mock attribute repo")
    assert byuCLI.lastCmdOutput == "attribute repo initialized"
    assert byuCLI.activeClient.attributeRepo is not None
    return byuCLI


@pytest.fixture(scope="module")
def attrAddedToRepo(attrRepoInitialized):
    byuCLI = attrRepoInitialized
    proverId = "Tyler"
    assert byuCLI.activeClient.attributeRepo.getAttributes(proverId) is None
    byuCLI.enterCmd("add attribute name=Tyler, age=17 for {}".format(proverId))
    assert byuCLI.lastCmdOutput == "attribute added successfully"
    assert byuCLI.activeClient.attributeRepo.getAttributes(proverId) is not None


@pytest.fixture(scope="module")
def storedCredAlias():
    return 'msccs'


@pytest.fixture(scope="module")
def storedCred(tylerCLI, storedCredAlias):
    # addNewKey(tylerCLI)
    assert len(tylerCLI.activeWallet.credNames) == 0
    tylerCLI.enterCmd("store credential {} as degree".format(storedCredAlias))
    assert len(tylerCLI.activeWallet.credNames) == 1
    assert tylerCLI.lastCmdOutput == "Credential stored"


@pytest.fixture(scope="module")
def listedCred(tylerCLI, storedCred):
    tylerCLI.enterCmd("list CRED")
    assert "Degree" in tylerCLI.lastCmdOutput


# TODO This test seems to be failing intermittently.
def testNodesCreatedOnPoolCLI(poolNodesCreated):
    pass


def testPhilCreatesNewKeypair(philPubKey):
    pass


def testPhilCreated(philCreated):
    pass


def testBYUCreated(byuCreated):
    pass


def testTylerCreated(tylerCreated):
    pass


def testBookStoreCreated(bookStoreCreated):
    pass


def testBYUAddsCredDef(byuAddsCredDef):
    pass


def testAnonCredsCLI(byuCLI, setup, philCreated, bookStoreCreated, byuCreated,
                     tylerCreated):
    pass


def testInitAttrRepo(attrRepoInitialized):
    pass


def testAddAttrToRepo(attrAddedToRepo):
    pass


def testReqCred(poolNodesCreated, tylerCreated, tylerCLI, byuCLI,
                attrAddedToRepo, byuAddsCredDef, tylerConnected):
    # # TODO: following step is to ensure "defaultClient.defaultIdentifier" is initialized
    # addNewKey(tylerCLI, byuCLI)

    credDefName = "Degree"
    credDefVersion = "1.0"
    issuerIdentifier = byuAddsCredDef
    proverId = tylerCLI.activeSigner.alias
    tylerCLI.enterCmd("request credential {} version {} from {} for {}"
                      .format(credDefName, credDefVersion, issuerIdentifier,
                              proverId))

    def chk():
        out = "Credential request for {} for {} {} is".format(proverId,
                                                                   credDefName,
                                                                   credDefVersion)
        assert tylerCLI.printeds[0]['msg'].startswith(out)
    tylerCLI.looper.run(eventually(chk, retryWait=1, timeout=15))


def testGenCred(poolNodesCreated, byuCLI, U):
    byuCLI.enterCmd("generate credential for {} with U {}".format(tylerPubKey, ))
    assert False


def testStoreCred(storedCred):
    pass


def testListCred(listedCred):
    pass


@pytest.fixture(scope="module")
def verifNonce(bookStoreCLI):
    # addNewKey(bookStoreCLI)
    bookStoreCLI.enterCmd("generate verification nonce")
    search = re.search("^Verification nonce is (.*)$",
                       bookStoreCLI.lastCmdOutput,
                       re.MULTILINE)
    assert search
    nonce = search.group(1)
    assert nonce
    return nonce


def testGenVerifNonce(verifNonce):
    pass


def testPrepareProof(tylerCLI, storedCred, verifNonce, storedCredAlias):
    """
    prepare proof of <credential alias> using nonce <nonce> for <revealed attrs>
    """
    revealeds = ("undergrad", )
    tylerCLI.enterCmd("prepare proof of {} using nonce {} for {}".
                      format(storedCredAlias, verifNonce, revealeds))
    assert "Proof is " in bookStoreCLI.lastCmdOutput


# def testGenCred(byuCLI):
#     addNewKey([byuCLI])
#     assert "Credential request is: {}".format("<need to put expected value>") == getLastCliPrintedMsg(byuCLI)
#
#
# def testInitIssuerAttribRepo(byuCLI):
#     pass

# def testAnonCredsCLI(cli):
#     """
#     Test to demonstrate anonymous credentials through Sovrin CLI.
#     """
#     cli.enterCmd("new keypair")
#     assert len(cli.defaultClient.signers) == 2
#     BYUPubKeyMsg = cli.lastPrintArgs['msg']
#     assert BYUPubKeyMsg.startswith('Public key')
#     BYUPubKey = BYUPubKeyMsg.split(" ")[-1]
#     cli.enterCmd("list ids")
#     cli.enterCmd("send NYM dest={}".format(BYUPubKey))  # TODO incomplete
#     cli.enterCmd("send GET_NYM dest={}".format(BYUPubKey))  # TODO incomplete
#     cli.enterCmd("send ATTRIB dest={key} "
#                  "raw={{email: mail@byu.edu}}".format(key=BYUPubKey))
#     cli.enterCmd(
#         'send CRED_DEF name="Qualifications" version="1.0" type=JC1 '
#         'ip=10.10.10.10 port=7897 keys={master_secret:<large number>, '
#         'n:<large number>, S:<large number>, Z:<large number>, '
#         'attributes: {'
#         '"first_name":R1, "last_name":R2, "birth_date":R3, "expire_date":R4, '
#         '"undergrad":R5, "postgrad":R6}}')
#     cli.enterCmd('new keypair BYU')
#     TylerPubKeyMsg = cli.lastPrintArgs['msg']
#     assert TylerPubKeyMsg.startswith('Public key')
#     TylerPubKey = TylerPubKeyMsg.split(" ")[-1]
#     cli.enterCmd('use keypair {}'.format(BYUPubKey))
#     assert cli.activeSigner.verstr == BYUPubKey
#     cli.enterCmd("send NYM dest={}".format(TylerPubKey))  # TODO incomplete
#     cli.enterCmd("send GET_NYM dest={}".format(TylerPubKey))  # TODO
# incomplete
#     cli.enterCmd("become {}".format(TylerPubKey))
#     assert cli.activeSigner.verstr == TylerPubKey
#     cli.enterCmd("send to {} saveas BYU-QUAL REQ_CRED name=Qualifications"
#                  " version=1.0 attrs=undergrad,postgrad".format(BYUPubKey))
#     cli.enterCmd("list CRED")
#     cli.enterCmd("become {}".format(TylerPubKey))
#     # TODO Verifier: BookStore must already exist on Sovrin
#     bookStorePubKey = None
#     cli.enterCmd("send proof of undergrad from CRED-BYU-QUAL to"
#                  " {}".format(bookStorePubKey))
