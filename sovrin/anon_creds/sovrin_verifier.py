from anoncreds.protocol.verifier import Verifier
from anoncreds.protocol.wallet.wallet import WalletInMemory

from sovrin.anon_creds.sovrin_public_repo import SovrinPublicRepo
from sovrin.client.wallet.wallet import Wallet


class SovrinVerifier(Verifier):
    def __init__(self, looper, client, wallet: Wallet):
        publicRepo = SovrinPublicRepo(looper=looper, client=client, wallet=wallet)
        verifierWallet = WalletInMemory(wallet.defaultId, publicRepo)
        super().__init__(verifierWallet)
