import pytest


from plenum.test.cli.conftest import cli, nodeRegsForCLI, looper,\
    createAllNodes
from plenum.test.cli.helper import newKeyPair
from plenum.test.cli.helper import newCLI
from sovrin.common.txn import SPONSOR, USER
from sovrin.test.cli.helper import sendNym
from sovrin.test.helper import createNym

"""
Test Plan:

5 CLI instances - 1 to run the consensus pool and 4 for clients.
4 clients - Phil, Tyler, BookStore and BYU

Phil is a pre-existing sponsor on Sovrin
BYU is a sponsor added by Phil to Sovrin
Tyler is a user added by BYU to Sovrin
BookStore is a user already on Sovrin

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


@pytest.fixture(scope="module")
def poolCLI(cli):
    return cli


@pytest.fixture(scope="module")
def byuCLI(nodeRegsForCLI, looper, tdir):
    return newCLI(nodeRegsForCLI, looper, tdir)


@pytest.fixture(scope="module")
def philCLI(nodeRegsForCLI, looper, tdir):
    return newCLI(nodeRegsForCLI, looper, tdir)


@pytest.fixture(scope="module")
def tylerCLI(nodeRegsForCLI, looper, tdir):
    return newCLI(nodeRegsForCLI, looper, tdir)


@pytest.fixture(scope="module")
def bookStoreCLI(nodeRegsForCLI, looper, tdir):
    return newCLI(nodeRegsForCLI, looper, tdir)


@pytest.fixture(scope="module")
def philPubKey(philCLI):
    return newKeyPair(philCLI)


@pytest.fixture(scope="module")
def bookStoreKey(bookStoreCLI):
    return newKeyPair(bookStoreCLI)


@pytest.fixture(scope="module")
def byuPubKey(byuCLI):
    return newKeyPair(byuCLI)


@pytest.fixture(scope="module")
def tylerPubKey(tylerCLI):
    return newKeyPair(tylerCLI, alias='Tyler')   # or should it be "forBYU"?


def createSponsor(nym, steward, cli):
    createNym(cli.looper, nym, steward, steward.signers[steward.name],
              SPONSOR)


# This method exists for debugging purposes.
def createUser(nym, sponsor, cli):
    createNym(cli.looper, nym, sponsor, sponsor.signers[sponsor.name], USER)


@pytest.fixture(scope="module")
def philCreated(philPubKey, steward, stewardCreated, poolCLI):
    createSponsor(philPubKey, steward, poolCLI)


# TODO debugging, remove
def testPhilCreated(philCreated):
    pass


@pytest.fixture(scope="module")
def bookStoreCreated(bookStorePubKey, steward, stewardCreated, poolCLI):
    createSponsor(bookStorePubKey, steward, poolCLI)


@pytest.fixture(scope="module")
def byuCreated(byuPubKey, philCreated, philCLI):
    sendNym(philCLI, byuPubKey, SPONSOR)


@pytest.fixture(scope="module")
def tylerCreated(tylerPubKey, byuCreated, byuCLI):
    sendNym(byuCLI, tylerPubKey, USER)


@pytest.fixture(scope="module")
def setup(poolCLI, philCLI, bookStoreCLI, byuCLI, tylerCLI):
    for node in poolCLI.nodes.values():
        for cli in [philCLI, bookStoreCLI, byuCLI, tylerCLI]:
            node.whitelistClient(cli.defaultClient.name)


def testAnonCredsCLI(poolCLI, philCLI, bookStoreCLI, byuCLI, tylerCLI,
                     setup, philCreated, bookStoreCreated, byuCreated,
                     tylerCreated):
    pass


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
