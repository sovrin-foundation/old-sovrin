import datetime
import random
from base58 import b58decode

import importlib
import importlib.util
import json
import os
from functools import partial
from typing import Tuple, Union

import libnacl.secret
from ledger.util import F

from anoncreds.protocol.types import AttribType, AttribDef
from anoncreds.protocol.utils import strToCryptoInteger, isCryptoInteger
from plenum.common.signing import serializeForSig
from plenum.common.txn import KEYS, DATA, ORIGIN
from plenum.common.types import f
from plenum.common.util import isHex, error, getConfig as PlenumConfig, \
    cryptonymToHex
from raet.nacling import Verifier


def getMsgWithoutSig(msg, sigFieldName=f.SIG.nm):
    msgWithoutSig = {}
    for k, v in msg.items():
        if k != sigFieldName:
            msgWithoutSig[k] = v
    return msgWithoutSig


def verifySig(identifier, signature, msg) -> bool:
    key = cryptonymToHex(identifier) if not isHex(
        identifier) else identifier
    ser = serializeForSig(msg)
    b64sig = signature.encode('utf-8')
    sig = b58decode(b64sig)
    vr = Verifier(key)
    return vr.verify(sig, ser)


def getSymmetricallyEncryptedVal(val, secretKey: Union[str, bytes]=None) -> \
        Tuple[str, str]:
    """
    Encrypt the provided value with symmetric encryption

    :param val: the value to encrypt
    :param secretKey: Optional key, if provided should be either in hex or bytes
    :return: Tuple of the encrypted value and secret key encoded in hex
    """

    if isinstance(val, str):
        val = val.encode("utf-8")
    if secretKey:
        if isHex(secretKey):
            secretKey = bytes(bytearray.fromhex(secretKey))
        elif not isinstance(secretKey, bytes):
            error("Secret key must be either in hex or bytes")
        box = libnacl.secret.SecretBox(secretKey)
    else:
        box = libnacl.secret.SecretBox()

    return box.encrypt(val).hex(), box.sk.hex()


def getSymmetricallyDecryptedVal(val, secretKey: Union[str, bytes]) -> str:
    if isHex(val):
        val = bytes(bytearray.fromhex(val))
    elif isinstance(val, str):
        val = val.encode("utf-8")
    if isHex(secretKey):
        secretKey = bytes(bytearray.fromhex(secretKey))
    elif isinstance(secretKey, str):
        secretKey = secretKey.encode()
    box = libnacl.secret.SecretBox(secretKey)
    return box.decrypt(val).decode()


def getInstalledConfig(installDir, configFile):
    configPath = os.path.join(installDir, configFile)
    if os.path.exists(configPath):
        spec = importlib.util.spec_from_file_location(configFile, configPath)
        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)
        return config
    else:
        raise FileNotFoundError("No file found at location {}".
                                format(configPath))


def getConfig(homeDir=None):
    plenumConfig = PlenumConfig(homeDir)
    sovrinConfig = importlib.import_module("sovrin.config")
    refConfig = plenumConfig
    refConfig.__dict__.update(sovrinConfig.__dict__)
    try:
        homeDir = os.path.expanduser(homeDir or "~")
        configDir = os.path.join(homeDir, ".sovrin")
        config = getInstalledConfig(configDir, "sovrin_config.py")
        refConfig.__dict__.update(config.__dict__)
    except FileNotFoundError:
        pass
    refConfig.baseDir = os.path.expanduser(refConfig.baseDir)
    return refConfig


def dateTimeEncoding(obj):
    if isinstance(obj, datetime.datetime):
        return int(obj.strftime('%s'))
    raise TypeError('Not sure how to serialize %s' % (obj,))


def getCredDefTxnData(claimDef):
    claimDef = claimDef.get()
    keys = claimDef[KEYS]
    keys["R"].pop("0")
    keys = {
        "master_secret_rand": int(keys.get("master_secret_rand")),
        "N": int(keys.get("N")),
        "S": int(keys.get("S")),
        "Z": int(keys.get("Z")),
        "attributes": {k: int(v) for k, v in keys["R"].items()}
    }
    claimDef[KEYS] = json.dumps(keys)
    return claimDef


def getNonce(length=32):
    hexChars = [hex(i)[2:] for i in range(0, 16)]
    return "".join([random.choice(hexChars) for i in range(length)])


# TODO: Bad interface, should return just attributes in a dictionary
def getEncodedAttrs(issuerId, attributes):
    attribTypes = []
    for nm in attributes.keys():
        attribTypes.append(AttribType(nm, encode=True))
    attribsDef = AttribDef(issuerId, attribTypes)
    attribs = attribsDef.attribs(**attributes).encoded()
    return {
        issuerId: next(iter(attribs.values()))
    }


def stringDictToCharmDict(dictionary):
    for k, v in dictionary.items():
        if isinstance(v, str):
            dictionary[k] = strToCryptoInteger(v)
    return dictionary


def charmDictToStringDict(dictionary):
    for k, v in dictionary.items():
        if isCryptoInteger(v) or isinstance(v, int):
            dictionary[k] = str(v)
    return dictionary


def getIssuerKeyAndExecuteClbk(wallet, client, displayer, loop, origin,
                                reference, clbk, pargs=None):

    chk = partial(wallet.isIssuerKeyComplete, origin, reference)
    if not chk():
        req = wallet.requestIssuerKey((origin, reference),
                                                 wallet.defaultId)
        client.submitReqs(req)
        if displayer:
            displayer("Getting Keys for the Claim Definition from Sovrin")
        if pargs is not None:
            loop.call_later(.2, ensureReqCompleted, loop, req.reqId, client,
                                    clbk, pargs, None, chk)
        else:
            loop.call_later(.2, ensureReqCompleted, loop, req.reqId, client,
                            clbk, None, None, chk)
    else:
        # Since reply and error will be none
        if pargs is None:
            clbk(None, None)
        else:
            clbk(None, None, *pargs)


def getCredDefIsrKeyAndExecuteCallback(wallet, client, displayer,
                                       loop, claimDefKey, clbk, pargs=None):

    # ATTENTION: This assumes that author of claimDef is same as the author of
    # issuerPublicKey
    def _getKey(result, error):
        data = json.loads(result.get(DATA))
        origin = data.get(ORIGIN)
        seqNo = data.get(F.seqNo.name)
        getIssuerKeyAndExecuteClbk(wallet, client, displayer, loop, origin,
                                   seqNo, clbk, pargs)

    chk = partial(wallet.isClaimDefComplete, claimDefKey)
    if not chk():
        req = wallet.requestClaimDef(claimDefKey, wallet.defaultId)
        client.submitReqs(req)
        displayer("Getting Claim Definition from Sovrin: {} {}"
                  .format(claimDefKey[0], claimDefKey[1]))
        loop.call_later(.2, ensureReqCompleted, loop, req.reqId, client,
                        _getKey, None, None, chk)
    else:
        claimDef = wallet.getClaimDef(key=claimDefKey)
        getIssuerKeyAndExecuteClbk(wallet, client, displayer, loop,
                                   claimDef.origin, claimDef.seqNo, clbk, pargs)


# TODO: Should have a timeout, should not have kwargs
def ensureReqCompleted(loop, reqId, client, clbk=None, pargs=None, kwargs=None,
                       cond=None):
    reply, err = client.replyIfConsensus(reqId)
    if reply is None and (cond is None or not cond()):
        loop.call_later(.2, ensureReqCompleted, loop,
                             reqId, client, clbk, pargs, kwargs, cond)
    elif clbk:
        # TODO: Do something which makes reply and error optional in the
        # callback.
        # TODO: This is kludgy, but will be resolved once we move away from
        # this callback pattern
        if pargs is not None and kwargs is not None:
            clbk(reply, err, *pargs, **kwargs)
        elif pargs is not None and kwargs is None:
            clbk(reply, err, *pargs)
        elif pargs is None and kwargs is not None:
            clbk(reply, err, **kwargs)
        else:
            clbk(reply, err)
