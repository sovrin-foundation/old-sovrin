import os

from plenum.common.pkg_util import check_deps

import sovrin

check_deps(sovrin)

from sovrin.common.plugin_helper import writeAnonCredPlugin
BASE_DIR = os.path.join(os.path.expanduser("~"), ".sovrin")
writeAnonCredPlugin(BASE_DIR)
