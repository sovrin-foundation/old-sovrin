import importlib
import importlib.util
import os
from typing import Tuple, Union

import libnacl.secret
from plenum.common.util import isHex, error


def getSymmetricallyEncryptedVal(val, secretKey: Union[str, bytes]=None) -> Tuple[str, str]:
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
        spec = importlib.util.spec_from_file_location(configFile,
                                                      configPath)
        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)
        return config
    else:
        raise FileNotFoundError("No file found at location {}".format(configPath))


def getConfig():
    refConfig = importlib.import_module("sovrin.config")
    try:
        homeDir = os.path.expanduser("~")
        configDir = os.path.join(homeDir, ".sovrin")
        config = getInstalledConfig(configDir, "sovrin_config.py")
        refConfig.__dict__.update(config.__dict__)
    except FileNotFoundError:
        pass
    return refConfig
