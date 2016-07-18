from sovrin.client.wallet import Wallet
from sovrin.persistence.wallet_storage_file import WalletStorageFile


def testCredentialDefinitionSecretKey(tdir, credDef1):
    serializedSk = credDef1.serializedSK
    walletStorage = WalletStorageFile(tdir)
    wallet = Wallet("testWallet", walletStorage)
    name, version = credDef1.name, credDef1.version
    wallet.addCredDefSk(name, version, serializedSk)
    assert serializedSk == wallet.getCredDefSk(name, version)
