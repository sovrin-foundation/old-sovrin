from plenum.common.txn import TYPE, IDENTIFIER, NONCE, DATA
from sovrin.agent.agent import Agent

from sovrin.agent.msg_types import AVAIL_CLAIM_LIST, CLAIMS
from plenum.common.types import f
from sovrin.common.util import verifySig

CLAIMS_LIST_FIELD = 'availableClaimsList'
CLAIMS_FIELD = 'claims'
ERROR = "ERROR"
REQ_MSG = "REQ_MSG"
SIGNATURE = 'signature'


import logging

# body = {
#     "type": <some type>,
#     "identifier": <id>,
#     "nonce": <nonce>,
#     "signature" : <sig>
# }


# TODO: We don't need to move wallet around
def getErrorResponse(wallet, reqMsg, errorMsg="Error"):
    invalidSigResp = {
        TYPE: ERROR,
        DATA: errorMsg,
        IDENTIFIER: wallet.defaultId,
        REQ_MSG: reqMsg
    }

    signature = wallet.signMsg(invalidSigResp, wallet.defaultId)
    invalidSigResp[SIGNATURE] = signature
    return invalidSigResp


# TODO: We don't need to move wallet around
def verifyAndGetLink(agent, wallet, msg):
    body, (frm, ha) = msg
    key = body.get(f.IDENTIFIER.nm)
    signature = body.get(SIGNATURE)
    isVerified = verifySig(key, signature, body)

    nonce = body.get(NONCE)
    link = wallet.getLinkByNonce(nonce)

    if not isVerified:
        agent.sendMessage(getErrorResponse(wallet, body, "Signature Rejected"),
                          destName=frm)
        logging.warning("Signature verification failed for msg: {}".
                      format(str(msg)))

        return False

    if link:
        link.remoteIdentifier = body.get(f.IDENTIFIER.nm)
        link.remoteEndPoint = ha
        return link
    else:
        logging.warning("Link not found for msg: {}".format(msg))
        agent.sendMessage(getErrorResponse(wallet, body, "No Such Link found"),
                          destName=frm)
        return None


# TODO: We don't need to move wallet around
def signAndSendToCaller(agent: Agent, wallet, resp, identifier, frm):
    signature = wallet.signMsg(resp, identifier)
    resp[SIGNATURE] = signature
    agent.sendMessage(resp, destName=frm)


def getCommonMsg(identifier, type):
    msg = {}
    msg[TYPE] = type
    msg[IDENTIFIER] = identifier
    return msg


def createAvailClaimListMsg(identifier, claimLists):
    msg = getCommonMsg(identifier, AVAIL_CLAIM_LIST)
    msg[CLAIMS_LIST_FIELD] = claimLists
    return msg


def createClaimsMsg(identifier, claims):
    msg = getCommonMsg(identifier, CLAIMS)
    msg[CLAIMS_FIELD] = claims
    return msg