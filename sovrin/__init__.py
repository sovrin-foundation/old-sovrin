import os

import sovrin
from plenum.common.util import check_deps

check_deps(sovrin)

from sovrin.common.plugin_helper import writeAnonCredPlugin
BASE_DIR = os.path.join(os.path.expanduser("~"), ".sovrin")
writeAnonCredPlugin(BASE_DIR)