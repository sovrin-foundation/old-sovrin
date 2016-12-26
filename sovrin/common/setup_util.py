import glob
import os
import shutil
from shutil import copyfile


class Setup:

    def __init__(self, basedir):
        self.base_dir = basedir

    def setupAll(self):
        self.setupTxns()
        self.setupSampleInvites()

    def setupTxns(self):
        import data

        pool_txn_file = os.path.join(self.base_dir, "pool_transactions_sandbox")
        pool_txn_local_file = os.path.join(self.base_dir, "pool_transactions_local")
        identity_txn_file = os.path.join(self.base_dir, "transactions_sandbox")
        identity_txn_local_file = os.path.join(self.base_dir, "transactions_local")

        dataDir = os.path.dirname(data.__file__)
        copyfile(os.path.join(dataDir, "pool_transactions_sandbox"), pool_txn_file)
        copyfile(os.path.join(dataDir, "pool_transactions_local"), pool_txn_local_file)
        copyfile(os.path.join(dataDir, "transactions_sandbox"), identity_txn_file)
        copyfile(os.path.join(dataDir, "transactions_local"), identity_txn_local_file)
        return self

    def setupSampleInvites(self):
        import sample
        sdir = os.path.dirname(sample.__file__)
        sidir = os.path.join(self.base_dir, "sample")
        os.makedirs(sidir, exist_ok=True)
        files = glob.iglob(os.path.join(sdir, "*.sovrin"))
        for file in files:
            if os.path.isfile(file):
                shutil.copy2(file, sidir)
        return self
