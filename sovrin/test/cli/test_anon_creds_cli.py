import pytest

from plenum.common.looper import Looper
from plenum.common.txn import TARGET_NYM
from plenum.test.cli.conftest import nodeRegsForCLI, createAllNodes, nodeNames
from plenum.test.cli.helper import newKeyPair, checkCmdValid, \
    assertAllNodesCreated
from sovrin.test.cli.helper import newCLI
from sovrin.common.txn import SPONSOR, USER, ROLE

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
def poolNodesCreated(poolCLI, nodeNames):
    createAllNodes(poolCLI)
    assertAllNodesCreated(poolCLI, nodeNames)


# TODO This test seems to be failing intermittently.
def testNodesCreatedOnPoolCLI(poolNodesCreated):
    pass


@pytest.fixture(scope="module")
def philPubKey(philCLI):
    return newKeyPair(philCLI)


@pytest.fixture(scope="module")
def trusteePubKey(trusteeCLI):
    return newKeyPair(trusteeCLI)


def testPhilCreatesNewKeypair(philPubKey):
    pass


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


def testPhilCreated(philCreated):
    pass


@pytest.fixture(scope="module")
def trusteeCreated(poolCLI, trusteePubKey):
    checkCmdValid(poolCLI, "add genesis transaction NYM dest={} role=STEWARD".
                  format(trusteePubKey))
    assert "Genesis transaction added." in poolCLI.lastCmdOutput


@pytest.fixture(scope="module")
def bookStoreCreated(bookStorePubKey, trusteeCreated, trusteeCLI):
    trusteeCLI.enterCmd("send NYM {dest}={bookStorePubKey} {role}={user}".
                        format(dest=TARGET_NYM,
                               bookStorePubKey=bookStorePubKey,
                               role=ROLE, user=USER))


@pytest.fixture(scope="module")
def byuCreated(byuPubKey, philCreated, philCLI, poolNodesCreated):
    philCLI.enterCmd("send NYM {dest}={byuPubKey} {role}={sponsor}".format(
        dest=TARGET_NYM, byuPubKey=byuPubKey, role=ROLE, sponsor=SPONSOR))


@pytest.fixture(scope="module")
def tylerCreated(tylerPubKey, byuCreated, byuCLI):
    byuCLI.enterCmd("send NYM {dest}={tylerPubKey} {role}={user}".format(
        dest=TARGET_NYM, tylerPubKey=tylerPubKey, role=ROLE, user=USER))


@pytest.fixture(scope="module")
def setup(poolCLI, philCLI, bookStoreCLI, byuCLI, tylerCLI):
    for node in poolCLI.nodes.values():
        for cli in [philCLI, bookStoreCLI, byuCLI, tylerCLI]:
            node.whitelistClient(cli.defaultClient.name)


def testAnonCredsCLI(setup, philCreated, bookStoreCreated, byuCreated,
                     tylerCreated):
    pass


def addNewKey(*clis):
    for cli in clis:
        cli.enterCmd("new key")


def testReqCred(tylerCLI, byuCLI):
    # TODO: following step is to ensure "defaultClient.defaultIdentifier" is initialized
    addNewKey(tylerCLI, byuCLI)

    credDefName ="Qualifications"
    credDefVersion = "1.0"
    issuerIdentifier = byuCLI.activeSigner.verstr
    tylerCLI.enterCmd("request credential {} version {} from {}".format(credDefName, credDefVersion, issuerIdentifier))
    assert "Credential request is: {}".format("<need to put expected value>") == tylerCLI.lastCmdOutput


@pytest.fixture(scope="module")
def attrRepoInitialized(byuCLI):
    addNewKey(byuCLI)
    assert byuCLI.activeClient.attributeRepo is None
    byuCLI.enterCmd("initialize mock attribute repo")
    assert byuCLI.lastCmdOutput == "attribute repo initialized"
    assert byuCLI.activeClient.attributeRepo is not None
    return byuCLI

def testInitAttrRepo(attrRepoInitialized):
    pass

@pytest.fixture(scope="module")
def attrRepoInitialized(byuCLI):
    pass


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
