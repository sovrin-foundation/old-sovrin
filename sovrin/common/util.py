import datetime
import random
from base64 import b64decode

import importlib
import importlib.util
import json
import os
from typing import Tuple, Union

import libnacl.secret
from plenum.common.signing import serializeForSig
from plenum.common.txn import KEYS
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
    sig = b64decode(b64sig)
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
