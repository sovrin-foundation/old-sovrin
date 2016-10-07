import pytest
import sovrin.anon_creds.cred_def as cred_def
import sovrin.anon_creds.issuer as issuer
from anoncreds.protocol.cred_def_secret_key import CredDefSecretKey
from sovrin.client.wallet.wallet import Wallet
# from sovrin.client.wallet.cred_def import CredDefSk, CredDefKey


# TODO: Confirm and update/remove
@pytest.mark.skipif(True, reason="What is being tested here. CredDefSk "
                                 "and CredDef do not have a one to one relation")
def testCredDefSecretKey(tdir, staticPrimes):
    GVT = issuer.AttribDef('gvt',
                           [issuer.AttribType('name', encode=True),
                            issuer.AttribType('age', encode=False),
                            issuer.AttribType('sex', encode=True)])
    sprimes = staticPrimes["prime1"]
    # sk = CredDefSecretKey(*sprimes)
    sk = CredDefSecretKey(*sprimes)
    cd = cred_def.CredDef(322324, GVT.attribNames())

    wallet = Wallet("testWallet")
    # cdsk = CredDefSk(name, version, serializedSk)
    wallet.addClaimDefSk(str(sk))
    stored = wallet.getClaimDefSk(CredDefKey(name, version))
    assert serializedSk == stored.secretKey
