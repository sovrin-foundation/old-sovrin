import pytest
import re

import sovrin.anon_creds.cred_def as cred_def

from plenum.common.looper import Looper
from plenum.common.txn import NAME, VERSION, ORIGIN
from plenum.test.cli.helper import newKeyPair, checkCmdValid, \
    checkClientConnected
from plenum.test.eventually import eventually
from sovrin.common.txn import SPONSOR, USER, CRED_DEF, ISSUER_KEY, REF
from sovrin.test.cli.helper import newCLI, ensureConnectedToTestEnv, \
    ensureNymAdded

"""
Test Plan:

6 CLI instances - 1 to run the consensus pool and 5 for clients.
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
def byuCLI(CliBuilder):
    yield from CliBuilder("byu")


@pytest.yield_fixture(scope="module")
def philCLI(CliBuilder):
    yield from CliBuilder("phil")


@pytest.yield_fixture(scope="module")
def trusteeCLI(CliBuilder):
    yield from CliBuilder("trustee")


@pytest.yield_fixture(scope="module")
def tylerCLI(CliBuilder):
    yield from CliBuilder("tyler")


@pytest.yield_fixture(scope="module")
def bookStoreCLI(CliBuilder):
    yield from CliBuilder("bookStore")


@pytest.fixture(scope="module")
def nodesSetup(philCreated, trusteeCreated, poolNodesCreated):
    pass


@pytest.fixture(scope="module")
def philPubKey(philCLI):
    return newKeyPair(philCLI)


@pytest.fixture(scope="module")
def trusteePubKey(trusteeCLI):
    return newKeyPair(trusteeCLI)


@pytest.fixture(scope="module")
def byuPubKey(byuCLI):
    return newKeyPair(byuCLI)


@pytest.fixture(scope="module")
def tylerPubKey(tylerCLI):
    return newKeyPair(tylerCLI, alias='Tyler')  # or should it be "forBYU"?


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
def philConnected(philCreated, philCLI, nodesSetup):
    ensureConnectedToTestEnv(philCLI)


@pytest.fixture(scope="module")
def bookStoreCreated(bookStorePubKey, trusteeCreated, trusteeCLI,
                     nodesSetup):
    ensureNymAdded(trusteeCLI, bookStorePubKey, USER)


@pytest.fixture(scope="module")
def bookStoreConnected(bookStoreCreated, bookStoreCLI, nodesSetup):
    ensureConnectedToTestEnv(bookStoreCLI)
    bookStoreCLI.logger.debug("Book store connected")


@pytest.fixture(scope="module")
def byuCreated(byuPubKey, philCreated, philCLI, nodesSetup):
    ensureNymAdded(philCLI, byuPubKey, SPONSOR)


@pytest.fixture(scope="module")
def tylerCreated(byuCreated, tylerPubKey, byuCLI, nodesSetup):
    ensureNymAdded(byuCLI, tylerPubKey)


@pytest.fixture(scope="module")
def tylerConnected(tylerCreated, tylerCLI):
    ensureConnectedToTestEnv(tylerCLI)


@pytest.fixture(scope="module")
def tylerStoresAttributesAsKnownToBYU(tylerCreated, tylerCLI, nodesSetup,
                                      byuCLI, tylerConnected):
    issuerId = byuCLI.activeWallet.defaultId
    checkCmdValid(tylerCLI,
                  "attribute known to {} first_name=Tyler, last_name=Ruff, "
                  "birth_date=12/17/1991, expiry_date=12/31/2101, "
                  "undergrad=True, "
                  "postgrad=False".format(issuerId))
    assert issuerId in tylerCLI.attributeRepo.attributes


@pytest.fixture(scope="module")
def credDefNameVersion():
    credDefName = "Degree"
    credDefVersion = "1.0"
    return credDefName, credDefVersion


@pytest.fixture(scope="module")
def byuAddsCredDef(byuCLI, byuCreated, tylerCreated, byuPubKey,
                   credDefNameVersion):
    credDefName, credDefVersion = credDefNameVersion
    # TODO tylerAdded ensures that activeClient is already set.
    """BYU writes a credential definition to Sovrin."""
    cmd = ("send CRED_DEF name={} version={} "
           "type=CL keys=undergrad,last_name,"
           "first_name,birth_date,postgrad,expiry_date".
           format(credDefName, credDefVersion))
    checkCmdValid(byuCLI, cmd)

    def checkCredAdded():
        txns = byuCLI.activeClient.getTxnsByType(CRED_DEF)
        assert any(txn[NAME] == credDefName and
                   txn[VERSION] == credDefVersion
                   for txn in txns)
        output = byuCLI.lastCmdOutput
        assert "credential definition is published" in output
        assert credDefName in output

    byuCLI.looper.run(eventually(checkCredAdded, retryWait=1, timeout=15))
    return byuCLI.activeWallet.defaultId


@pytest.fixture(scope="module")
def byuAddsIssuerKey(byuCLI, byuAddsCredDef, credDefNameVersion):
    origin = byuAddsCredDef
    key = (*credDefNameVersion, origin)
    claimDef = byuCLI.activeWallet.getClaimDef(key=key)
    cmd = ("send ISSUER_KEY ref={}" .format(claimDef.seqNo))
    checkCmdValid(byuCLI, cmd)

    def checkIsKAdded():
        assert byuCLI.activeWallet.getIssuerPublicKey((origin, claimDef.seqNo))
        output = byuCLI.lastCmdOutput
        assert "issuer key is published" in output

    byuCLI.looper.run(eventually(checkIsKAdded, retryWait=1, timeout=15))
    return byuCLI.activeWallet.getIssuerPublicKey((origin, claimDef.seqNo))


@pytest.fixture(scope="module")
def tylerPreparedU(nodesSetup, tylerCreated, tylerCLI, byuCLI,
                   attrAddedToRepo, byuAddsCredDef, byuAddsIssuerKey,
                   credDefNameVersion, tylerConnected,
                   tylerStoresAttributesAsKnownToBYU):
    credDefName, credDefVersion = credDefNameVersion
    issuerIdentifier = byuAddsCredDef
    proverName = tylerCLI.activeWallet.defaultAlias
    checkCmdValid(tylerCLI, "request credential {} version {} from {} for {}"
                  .format(credDefName, credDefVersion, issuerIdentifier,
                          proverName))

    def chk():
        out = "Credential request for {} for {} {} is".format(proverName,
                                                              credDefName,
                                                              credDefVersion)
        assert out in tylerCLI.lastCmdOutput

    tylerCLI.looper.run(eventually(chk, retryWait=1, timeout=15))
    U = None
    proofId = None
    pat = re.compile(
        "Credential id is ([a-f0-9\-]+) and U is ([0-9]+\s+mod\s+[0-9]+)")
    m = pat.search(tylerCLI.lastCmdOutput)
    if m:
        proofId, U = m.groups()
    return proofId, U


@pytest.fixture(scope="module")
def byuCreatedCredential(nodesSetup, byuCLI, tylerCLI,
                         tylerStoresAttributesAsKnownToBYU, tylerPreparedU,
                         credDefNameVersion):
    credDefName, credDefVersion = credDefNameVersion
    proofId, U = tylerPreparedU
    proverId = tylerCLI.activeWallet.defaultAlias
    checkCmdValid(byuCLI, "generate credential for {} for {} version {} with {}"
                  .format(proverId, credDefName, credDefVersion, U))
    assert "Credential:" in byuCLI.lastCmdOutput
    pat = re.compile(
        "A\s*=\s*([mod0-9\s]+), e\s*=\s*([mod0-9\s]+), vprimeprime\s*=\s*(["
        "mod0-9\s]+)")
    m = pat.search(byuCLI.lastCmdOutput)
    if m:
        A, e, vprimeprime = m.groups()
        return A, e, vprimeprime


@pytest.fixture(scope="module")
def attrRepoInitialized(byuCLI, byuCreated):
    assert byuCLI.attributeRepo is None
    byuCLI.enterCmd("initialize mock attribute repo")
    assert byuCLI.lastCmdOutput == "attribute repo initialized"
    assert byuCLI.attributeRepo is not None
    return byuCLI


@pytest.fixture(scope="module")
def attrAddedToRepo(attrRepoInitialized):
    byuCLI = attrRepoInitialized
    proverId = "Tyler"
    assert byuCLI.attributeRepo.getAttributes(proverId) is None
    checkCmdValid(byuCLI, "add attribute first_name=Tyler, last_name=Ruff, "
                          "birth_date=12/17/1991, expiry_date=12/31/2101, "
                          "undergrad=True, "
                          "postgrad=False for {}".format(proverId))
    assert byuCLI.lastCmdOutput == \
           "attribute added successfully for prover id {}".format(proverId)
    assert byuCLI.attributeRepo.getAttributes(proverId) is not None


@pytest.fixture(scope="module")
def storedCredAlias():
    return 'CRED-BYU-QUAL'


@pytest.fixture(scope="module")
def revealedAtrr():
    return "undergrad"


@pytest.fixture(scope="module")
def storedCred(tylerCLI, storedCredAlias, byuCreatedCredential,
               credDefNameVersion, byuPubKey, byuCLI, tylerPreparedU):
    proofId, U = tylerPreparedU
    assert len(tylerCLI.activeWallet.credNames) == 0
    checkCmdValid(tylerCLI, "store credential A={}, e={}, vprimeprime={} for "
                            "credential {} as {}".format(*byuCreatedCredential,
                                                         proofId,
                                                         storedCredAlias))
    assert len(tylerCLI.activeWallet.credNames) == 1
    assert tylerCLI.lastCmdOutput == "Credential stored"


@pytest.fixture(scope="module")
def listedCred(tylerCLI, storedCred, storedCredAlias):
    credName = storedCredAlias
    tylerCLI.enterCmd("list CRED")
    assert credName in tylerCLI.lastCmdOutput


@pytest.fixture(scope="module")
def preparedProof(tylerCLI, storedCred, verifNonce, storedCredAlias,
                  tylerPreparedU, revealedAtrr):
    """
       prepare proof of <credential alias> using nonce <nonce> for <revealed
       attrs>
       """
    checkCmdValid(tylerCLI, "prepare proof of {} using nonce {} for {}".
                  format(storedCredAlias, verifNonce, revealedAtrr))
    assert tylerCLI.lastCmdOutput.startswith("Proof is:")
    pat = re.compile("Proof is: (.+)$")
    m = pat.search(tylerCLI.lastCmdOutput)
    if m:
        proof = m.groups()[0]
        return proof


@pytest.fixture(scope="module")
def verifNonce(bookStoreCLI, bookStoreConnected):
    checkCmdValid(bookStoreCLI, "generate verification nonce")
    search = re.search("^Verification nonce is (.*)$",
                       bookStoreCLI.lastCmdOutput,
                       re.MULTILINE)
    assert search
    nonce = search.group(1)
    assert nonce
    return nonce


def testNodesCreatedOnPoolCLI(nodesSetup):
    pass


def testPhilCreatesNewKeypair(philPubKey):
    pass


def testPhilCreated(philCreated):
    pass


def testBYUCreated(byuCreated):
    pass


def testTylerCreated(tylerCreated):
    pass


def testBYUAddsCredDef(byuAddsCredDef):
    pass


def testBYUAddsIssuerKey(byuAddsIssuerKey):
    pass


def testBookStoreCreated(bookStoreCreated):
    pass


def testInitAttrRepo(attrRepoInitialized):
    pass


def testAddAttrToRepo(attrAddedToRepo):
    pass


def testTylerAddsBYUKnownAttributes(tylerConnected,
                                    tylerStoresAttributesAsKnownToBYU):
    pass


def testReqCred(tylerPreparedU):
    pass


def testGenCred(byuCreatedCredential):
    pass


def testStoreCred(byuCreatedCredential, tylerCLI, storedCred):
    pass


def testListCred(byuCreatedCredential, storedCred, listedCred):
    pass


def testGenVerifNonce(verifNonce):
    pass


def testPrepareProof(preparedProof):
    """
    prepare proof of <credential alias> using nonce <nonce> for <revealed attrs>
    """
    pass


def testVerifyProof(preparedProof, bookStoreCLI, bookStoreConnected,
                    revealedAtrr):
    checkCmdValid(bookStoreCLI, "verify status is {} in proof {}"
                  .format(revealedAtrr, preparedProof))

    def chk():
        out = "Proof verified successfully"
        # TODO: Find out why this cant be done using lastCmdOutput
        assert out in [o['msg'] for o in bookStoreCLI.printeds]

    bookStoreCLI.looper.run(eventually(chk, retryWait=1, timeout=15))


def testStrTointeger(philCLI):
    s = "10516306386726286019672155171905126058592128650909982334149995178986" \
        "73041451400057431499605181158943503786100424862329515980934309973855" \
        "43633459501210681944476644996687930156869752481111735518704772442711" \
        "32920275895833800639728797016576397009810826557954409165313076062707" \
        "47896162050899399482026144231267729603011571552636739780628091227072" \
        "28494440544261006174039338285983989215624037187355611285872388705963" \
        "92055048166735124754509553245871190284165785505721277426571438891467" \
        "29655980852237635516682805164630997143549509439718228947745728568873" \
        "10731055328114318748960481507556680409317152030165076731535544266284" \
        "97344415043361299612836649013009811372870411059001759588530641278227" \
        "57354566174219004200609850136175582501103513229230409927604286888631" \
        "75800846390172847752237996720841151109593372359247207743122920739798" \
        "82866204968535074422800013404448542530994158870307914545156283091106" \
        "37115909820184225905798609572477314653567493587473310985742198863055" \
        "06587955028364104696132700843261021195133842375205258169506504549494" \
        "29889788207677394004011987322884615951959337492651215535237394870438" \
        "68207276588075432476520034758009673995991879029329589895963661033408" \
        "38408748799357047790102800661841526315212047820316288243833530421278" \
        "49220882904454974822462754425677230712125202287893066412470634696970" \
        "66231997995973482950088138763475549481696937039149518646360622862464" \
        "50748921772308784787805092674994571742201612047716630085199077191636" \
        "4373279780274868194055796561573920450780745745182897139619 " \
        "mod " \
        "17110939584351099093696670018389609679123235613458011379970547802872" \
        "97845880693420604905384069214955803671128011572590150617889133331019" \
        "87767287757635214004081316079534532746984329504603946034535455284745" \
        "68133662112187368369825445516306247795885376833794985882661431944005" \
        "56774611220327379825358059647159046779617474158142416357512573091169" \
        "21742481914530128558200847594640862842694412593095042311521914864035" \
        "92285503796577197095138752688777268824531776522996865594649891459269" \
        "52651057269564711873631049284032786289125795739748747186484622340137" \
        "09891887981964130042842902760426557389856693142665410665604318462645" \
        "45166408163005165263132781945822482669510449665227350126593542756259" \
        "49016086602052739665101758864010913600376302252580874442010241767160" \
        "04738260768285471771028761205014421557974943906343096963043686300824" \
        "41915506224275376177925859647928995537185609046742534998874286371343" \
        "66703575716284805303334603968057185045321034098727958620904195146881" \
        "865483244806147104667605098138613899840626729916612169723470228930801507396158440259774040553984850335586645194467365045176677506537296253654429662975816874630847874003647935529333964941855401786336352853043803498640759072173609203160413437402970023625421911392981092263211748047448929085861379410272047860536995972453496075851660446485058108906037436369067625674495155937598646143535510599911729010586276679305856525112130907097314388354485920043436412137797426978774012573863335500074359101826932761239032674620096110906293228090163"
    i = philCLI.getCryptoInteger(s)
    assert str(i) == s
