import json

import pytest
from anoncreds.protocol.utils import encodeAttrs

from plenum.client.signer import SimpleSigner
from plenum.common.txn import ORIGIN, TARGET_NYM, ROLE, TXN_TYPE, DATA, TXN_ID
from plenum.common.util import randomString, adict
from plenum.test.eventually import eventually
from plenum.test.helper import genHa, genTestClient, checkSufficientRepliesRecvd
from sovrin.common.txn import USER, ADD_NYM
from sovrin.test.helper import submitAndCheck, genConnectedTestAnonCredsRole, \
    createNym, TestVerifier, TestIssuer, TestProver


@pytest.fixture(scope="module")
def issuerSigner():
    signer = SimpleSigner()
    return signer


@pytest.fixture(scope="module")
def proverSigner():
    signer = SimpleSigner()
    return signer


@pytest.fixture(scope="module")
def verifierSigner():
    signer = SimpleSigner()
    return signer


@pytest.fixture(scope="module")
def issuerHa():
    return genHa()


@pytest.fixture(scope="module")
def verifierHa():
    return genHa()


@pytest.fixture(scope="module")
def issuerName():
    return randomString(6)


@pytest.fixture(scope="module")
def verifierName():
    return randomString(6)


@pytest.fixture(scope="module")
def proverAttributeNames():
    return sorted(['name', 'age', 'sex', 'country'])


@pytest.fixture(scope="module")
def proverAttributes():
    return {'name': 'Mario', 'age': '25', 'sex': 'Male', 'country': 'Italy'}


@pytest.fixture(scope="module")
def encodedProverAttributes(proverAttributes):
    return encodeAttrs(proverAttributes)


@pytest.fixture(scope="module")
def addedIPV(looper, genned, addedSponsor, sponsor, sponsorSigner,
             issuerSigner, proverSigner, verifierSigner, issuerHA, proverHA, verifierHA):
    """
    Added issuer, prover and verifier to sovrin
    """
    sponsNym = sponsorSigner.verstr
    iNym = issuerSigner.verstr
    pNym = proverSigner.verstr
    vNym = verifierSigner.verstr

    # TODO Why is prover not added here?
    for nym, ha in ((iNym, issuerHA), (pNym, proverHA), (vNym, verifierHA)):
        op = {
            ORIGIN: sponsNym,
            TARGET_NYM: nym,
            TXN_TYPE: ADD_NYM,
            ROLE: USER,
            DATA: json.dumps({'ha': ha})
        }
        submitAndCheck(looper, sponsor, op, identifier=sponsNym)
    createNym(looper, proverSigner, sponsor, sponsorSigner, USER)


@pytest.fixture(scope="module")
def issuer(addedIPV, looper, nodeSet, tdir, issuerSigner, issuerHa,
           issuerName):
    cliNodeReg = nodeSet.nodeReg.extractCliNodeReg()
    return genConnectedTestAnonCredsRole(typ=TestIssuer,
                                           name=issuerName,
                                           p2pHa=issuerHa,
                                           looper=looper,
                                           nodes=nodeSet,
                                           nodeReg=cliNodeReg,
                                           tmpdir=tdir,
                                           signer=issuerSigner)


@pytest.fixture(scope="module")
def verifier(addedIPV, looper, nodeSet, tdir, verifierSigner, verifierHa,
             verifierName):
    cliNodeReg = nodeSet.nodeReg.extractCliNodeReg()
    return genConnectedTestAnonCredsRole(typ=TestVerifier,
                                           name=verifierName,
                                           p2pHa=verifierHa,
                                           looper=looper,
                                           nodes=nodeSet,
                                           nodeReg=cliNodeReg,
                                           tmpdir=tdir,
                                           signer=verifierSigner)


@pytest.fixture(scope="module")
def prover(addedIPV, looper, nodeSet, tdir, verifierSigner, verifierHa,
           verifierName):
    cliNodeReg = nodeSet.nodeReg.extractCliNodeReg()
    return genConnectedTestAnonCredsRole(typ=TestProver,
                                           name=verifierName,
                                           p2pHa=verifierHa,
                                           looper=looper,
                                           nodes=nodeSet,
                                           nodeReg=cliNodeReg,
                                           tmpdir=tdir,
                                           signer=verifierSigner)


@pytest.fixture(scope="module")
def issuerAddedPK_I(addedIPV, looper, nodeSet, issuer, proverAttributeNames):
    req, = issuer.addPkiToLedger(proverAttributeNames)
    looper.run(eventually(checkSufficientRepliesRecvd,
                          issuer.sovrinClient.inBox,
                          req.reqId,
                          nodeSet.f,
                          retryWait=1,
                          timeout=5))
    reply, = issuer.sovrinClient.getReply(req.reqId)
    r = adict()
    r[TXN_ID] = reply.result[TXN_ID]
    return r


def testAnonCredFlow(issuerAddedPK_I, issuer, verifier, prover, looper):
    looper.runFor(3)
