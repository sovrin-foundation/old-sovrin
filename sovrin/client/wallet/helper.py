from plenum.common.txn import TYPE, IDENTIFIER
from sovrin.agent.agent import Agent

from sovrin.agent.msg_types import AVAIL_CLAIM_LIST, CLAIMS
from plenum.common.types import f
from sovrin.common.util import verifySig

CLAIMS_LIST_FIELD = 'availableClaimsList'
CLAIMS_FIELD = 'claims'
import logging

# body = {
#     "type": <some type>,
#     "identifier": <id>,
#     "nonce": <nonce>,
#     "signature" : <sig>
# }


# TODO: We don't need to move wallet around
def getErrorResponse(wallet, errorMsg):
    invalidSigResp = {
        "error": errorMsg
    }
    signature = wallet.signMsg(invalidSigResp, wallet.defaultId)
    invalidSigResp['signature'] = signature
    return invalidSigResp

# TODO: We don't need to move wallet around
def getInvalidSigResponse(wallet):
    return getErrorResponse(wallet, "Signature Rejected")

# TODO: We don't need to move wallet around
def getLinkNotFoundResponse(wallet):
    return getErrorResponse(wallet, "No Such Link found")


# TODO: We don't need to move wallet around
def verifyAndGetLink(agent, wallet, msg):
    body, (frm, ha) = msg
    key = body.get(f.IDENTIFIER.nm)
    signature = body.get("signature")
    isVerified = verifySig(key, signature, body)

    if not isVerified:
        agent.sendMessage(getInvalidSigResponse(wallet), destName=frm)
        logging.error("Signature verification failed for msg: {}".format(msg))
        return False

    nonce = body.get("nonce")
    link = wallet.getLinkByNonce(nonce)
    if link:
        link.remoteIdentifier = body.get(f.IDENTIFIER.nm)
        link.remoteEndPoint = ha
        return link
    else:
        agent.sendMessage(getLinkNotFoundResponse(wallet), destName=frm)
        logging.error("Link not found for msg: {}".format(msg))
        return None


# TODO: We don't need to move wallet around
def signAndSendToCaller(agent: Agent, wallet, resp, identifier, frm):
    signature = wallet.signMsg(resp, identifier)
    resp['signature'] = signature
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