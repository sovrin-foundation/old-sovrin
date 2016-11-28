from anoncreds.protocol.issuer import Issuer
from anoncreds.protocol.repo.attributes_repo import AttributeRepo
from anoncreds.protocol.wallet.issuer_wallet import IssuerWalletInMemory

from sovrin.anon_creds.sovrin_public_repo import SovrinPublicRepo
from sovrin.client.wallet.wallet import Wallet


class SovrinIssuer(Issuer):
    def __init__(self, looper, client, wallet: Wallet, attrRepo: AttributeRepo):
        publicRepo = SovrinPublicRepo(looper=looper, client=client, wallet=wallet)
        issuerWallet = IssuerWalletInMemory(wallet.defaultId, publicRepo)
        super().__init__(issuerWallet, attrRepo)
