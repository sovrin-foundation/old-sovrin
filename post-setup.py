from sovrin.common.setup_util import Setup
import os
BASE_DIR = os.path.join(os.path.expanduser("~"), ".sovrin")
Setup(BASE_DIR).setupAll()