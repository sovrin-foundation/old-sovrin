import sovrin.anon_creds.cred_def as cred_def
import sovrin.anon_creds.issuer as issuer
from anoncreds.protocol.cred_def_secret_key import CredDefSecretKey
from sovrin.client.wallet.wallet import Wallet
from sovrin.client.wallet.cred_def import CredDefSk, CredDefKey


def testCredDefSecretKey(tdir, staticPrimes):
    GVT = issuer.AttribDef('gvt',
                           [issuer.AttribType('name', encode=True),
                            issuer.AttribType('age', encode=False),
                            issuer.AttribType('sex', encode=True)])
    sprimes = staticPrimes["prime1"]
    sk = CredDefSecretKey(*sprimes)
    cd = cred_def.CredDef(322324, GVT.attribNames())

    wallet = Wallet("testWallet")
    cdsk = CredDefSk(name, version, serializedSk)
    wallet.addCredDefSk(cdsk)
    stored = wallet.getCredDefSk(CredDefKey(name, version))
    assert serializedSk == stored.secretKey
