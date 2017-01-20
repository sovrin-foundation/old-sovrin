import glob
import os
import shutil
from shutil import copyfile

from sovrin.common.constants import Environment
from sovrin.config import ENVS


class Setup:

    def __init__(self, basedir):
        self.base_dir = basedir

    def setupAll(self):
        self.setupTxns()
        self.setupSampleInvites()

    def setupTxns(self):
        import data
        dataDir = os.path.dirname(data.__file__)

        tmpENVS = {
            "local": Environment("pool_transactions_local",
                                 "transactions_local"),
        }
        tmpENVS.update(ENVS)
        for envName, env in tmpENVS.items():
            for _, fileName in env._asdict().items():
                sourceFilePath = os.path.join(dataDir, fileName)
                if os.path.exists(sourceFilePath):
                    destFilePath = os.path.join(self.base_dir, fileName)
                    copyfile(sourceFilePath, destFilePath)

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
