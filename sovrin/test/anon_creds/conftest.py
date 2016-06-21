import json

import pytest
from charm.core.math.integer import integer

from anoncreds.protocol.utils import encodeAttrs

from plenum.client.signer import SimpleSigner

from plenum.test.eventually import eventually
from plenum.test.helper import genHa, checkSufficientRepliesRecvd
from sovrin.common.txn import USER, NYM, CRED_DEF
from sovrin.test.helper import submitAndCheck, addNym
from charm.core.math.integer import integer

from plenum.common.txn import ORIGIN, TXN_TYPE, NAME, VERSION, TYPE, IP,\
    PORT, KEYS, DATA
from anoncreds.protocol.issuer import Issuer

from sovrin.common.txn import CRED_DEF, GET_CRED_DEF
from sovrin.test.helper import addUser, submitAndCheck, genTestClient


# TODO Make a fixture for creating a client with a anon-creds features
#  enabled.
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
def issuerHA():
    return genHa()


@pytest.fixture(scope="module")
def proverHA():
    return genHa()


@pytest.fixture(scope="module")
def verifierHA():
    return genHa()


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
             issuerSigner, proverSigner, verifierSigner, issuerHA, proverHA,
             verifierHA):
    """
    Creating nyms for issuer, prover and verifier on Sovrin.
    """
    sponsNym = sponsorSigner.verstr
    iNym = issuerSigner.verstr
    pNym = proverSigner.verstr
    vNym = verifierSigner.verstr

    for nym, ha in ((iNym, issuerHA), (pNym, proverHA), (vNym, verifierHA)):
        addNym(ha, looper, nym, sponsNym, sponsor)


# @pytest.fixture(scope="module")
# def issuerAddedPK_I(addedIPV, looper, nodeSet, issuerAdded,
#                     proverAttributeNames):
#     req, = addedIssuer.addPkiToLedger(proverAttributeNames)
#     looper.run(eventually(checkSufficientRepliesRecvd,
#                           issuerAdded.inBox,
#                           req.reqId,
#                           nodeSet.f,
#                           retryWait=1,
#                           timeout=5))
#     reply, = addedIssuer.getReply(req.reqId)
#     r = adict()
#     r[TXN_ID] = reply.result[TXN_ID]
#     return r


@pytest.fixture(scope="module")
def attrNames():
    return "first_name", "last_name", "birth_date", "expire_date", \
           "undergrad", "postgrad"


@pytest.fixture(scope="module")
def issuer(attrNames):
    p_prime = integer(156991571687241757560913999612105108587468535208804851513244305347791502397013251234580937586571597031916037838033046034770771173926507265437617855415940646572556208146631362944594503201021036235697827847650635607984173023170017730379016569941848350333948723947742719519249330208387815146482288223677189982933)
    q_prime = integer(168694778973832439908851228779255302004773421133839849056373974229420312328526255272439631222790798583346447915579287992909455456865305700322580981926848432022408208416487374085454534271452543138205715733881167962673142093415926617886691354844318260877624181326227800612850621357390310851043996607517675746483)
    return Issuer(attrNames, True, p_prime, q_prime)


@pytest.fixture(scope="module")
def credDef(issuer):
    pk = issuer.PK
    return {
        NAME: "Qualifications",
        VERSION: "1.0",
        TYPE: "CL",
        IP: "127.0.0.1",
        PORT: 7897,
        KEYS: json.dumps({
            "master_secret_rand": int(pk.R.pop("0")),
            "N": int(pk.N),
            "S": int(pk.S),
            "Z": int(pk.Z),
            "attributes": {k: int(v) for k, v in pk.R.items()}
        })
    }


@pytest.fixture(scope="module")
def credentialDefinitionAdded(genned, updatedSteward, addedSponsor, sponsor,
                            sponsorSigner, looper, tdir, nodeSet, credDef):
    op = {
        ORIGIN: sponsorSigner.verstr,
        TXN_TYPE: CRED_DEF,
        DATA: credDef
    }

    return submitAndCheck(looper, sponsor, op,
                          identifier=sponsorSigner.verstr)
