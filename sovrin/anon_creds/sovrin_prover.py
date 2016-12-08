from anoncreds.protocol.prover import Prover
from anoncreds.protocol.wallet.prover_wallet import ProverWalletInMemory

from sovrin.anon_creds.sovrin_public_repo import SovrinPublicRepo
from sovrin.client.wallet.wallet import Wallet


class SovrinProver(Prover):
    def __init__(self, looper, client, wallet: Wallet):
        publicRepo = SovrinPublicRepo(looper=looper, client=client, wallet=wallet)
        proverWallet = ProverWalletInMemory(wallet.name, publicRepo)
        super().__init__(proverWallet)
