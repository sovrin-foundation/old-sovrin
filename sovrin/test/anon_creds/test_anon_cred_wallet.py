from sovrin.anon_creds.cred_def import CredDef
from sovrin.anon_creds.issuer import AttribDef, AttribType
from sovrin.client.wallet import Wallet
from sovrin.persistence.wallet_storage_file import WalletStorageFile

GVT = AttribDef('gvt',
                [AttribType('name', encode=True),
                  AttribType('age', encode=False),
                  AttribType('sex', encode=True)])


def testCredDefSecretKey(tdir):
    P_PRIME1, Q_PRIME1 = CredDef.getStaticPPrime("prime1"), CredDef.getStaticQPrime("prime1")
    primes = dict(p_prime=P_PRIME1, q_prime=Q_PRIME1)
    gvtCredDef = CredDef(GVT.attribNames(), **primes)
    serializedSk = gvtCredDef.serializedSK
    walletStorage = WalletStorageFile(tdir)
    wallet = Wallet("testWallet", walletStorage)
    name, version = gvtCredDef.name, gvtCredDef.version
    wallet.addCredDefSk(name, version, serializedSk)
    assert serializedSk == wallet.getCredDefSk(name, version)
