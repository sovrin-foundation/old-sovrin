import os

import sovrin


class HasFileStorage:

    def __init__(self, name, dataDir=None):
        self.name = name
        self.packagePath = sovrin.__file__
        self.currentPath = os.path.dirname(self.packagePath)
        self.dataDir = dataDir if dataDir else ""

    def getDataLocation(self):
        return os.path.join(self.currentPath, self.dataDir, self.name)
