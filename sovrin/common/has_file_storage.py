import os

import sovrin


class HasFileStorage:

    def __init__(self, name, baseDir=None, dataDir=None):
        self.name = name
        self.packagePath = sovrin.__file__
        self.basePath = baseDir or os.path.dirname(self.packagePath)
        self.dataDir = dataDir if dataDir else ""

    def getDataLocation(self):
        return os.path.join(self.basePath, self.dataDir, self.name)
