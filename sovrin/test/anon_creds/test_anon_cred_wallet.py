from sovrin.client.wallet import Wallet
from sovrin.persistence.wallet_storage_file import WalletStorageFile
from anoncreds.test.conftest import gvtCredDef, gvtAttrNames, primes1

def testCredentialDefinitionSecretKey(tdir, gvtCredDef):
    serializedSk = gvtCredDef.serializedSK
    walletStorage = WalletStorageFile(tdir)
    wallet = Wallet("testWallet", walletStorage)
    name, version = gvtCredDef.name, gvtCredDef.version
    wallet.addCredDefSk(name, version, serializedSk)
    assert serializedSk == wallet.getCredDefSk(name, version)
