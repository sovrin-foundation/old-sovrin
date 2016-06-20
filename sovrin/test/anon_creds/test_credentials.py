import json

import pytest
from charm.core.math.integer import integer

from plenum.test.eventually import eventually
from plenum.test.helper import checkSufficientRepliesRecvd

from plenum.common.txn import ORIGIN, TXN_TYPE, NAME, VERSION, TYPE, IP, PORT, \
    KEYS, DATA, TARGET_NYM
from anoncreds.protocol.issuer import Issuer

from sovrin.common.txn import CRED_DEF, GET_CRED_DEF
from sovrin.test.helper import addUser, submitAndCheck, genTestClient


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

    return submitAndCheck(looper, sponsor, op, identifier=sponsorSigner.verstr)


def testIssuerWritesCredDef(credentialDefinitionAdded):
    """
    A credential definition is added
    """
    pass


def testProverGetsCredDef(credentialDefinitionAdded, userSignerA, tdir, nodeSet,
                          looper, sponsorSigner, credDef):
    """
    A credential definition is received
    """
    user = genTestClient(nodeSet, signer=userSignerA, tmpdir=tdir)
    looper.add(user)
    looper.run(user.ensureConnectedToNodes())
    op = {
        ORIGIN: userSignerA.verstr,
        TARGET_NYM: sponsorSigner.verstr,
        TXN_TYPE: GET_CRED_DEF,
        DATA: {
            NAME: credDef[NAME],
            VERSION: credDef[VERSION]
        }
    }
    req, = user.submit(op, identifier=userSignerA.verstr)
    looper.run(eventually(checkSufficientRepliesRecvd, user.inBox, req.reqId, nodeSet.f,
               retryWait=1, timeout=5))
    reply, status = user.getReply(req.reqId)
    assert status == "CONFIRMED"
    recvdCredDef = json.loads(reply[DATA])
    assert recvdCredDef[NAME] == credDef[NAME]
    assert recvdCredDef[VERSION] == credDef[VERSION]
    # TODO: Need to check equality of keys too

