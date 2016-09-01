import sovrin.anon_creds.cred_def as cred_def
import sovrin.anon_creds.issuer as issuer
from sovrin.client.wallet import Wallet
from sovrin.persistence.wallet_storage_file import WalletStorageFile


def testCredDefSecretKey(tdir):
    GVT = issuer.AttribDef('gvt',
                           [issuer.AttribType('name', encode=True),
                            issuer.AttribType('age', encode=False),
                            issuer.AttribType('sex', encode=True)])
    P_PRIME1, Q_PRIME1 = cred_def.CredDef.getStaticPPrime("prime1"), cred_def.CredDef.getStaticQPrime("prime1")
    primes = dict(p_prime=P_PRIME1, q_prime=Q_PRIME1)
    gvtCredDef = cred_def.CredDef(GVT.attribNames(), **primes)
    serializedSk = gvtCredDef.serializedSK
    walletStorage = WalletStorageFile(tdir)
    wallet = Wallet("testWallet", walletStorage)
    name, version = gvtCredDef.name, gvtCredDef.version
    wallet.addCredDefSk(name, version, serializedSk)
    assert serializedSk == wallet.getCredDefSk(name, version)
