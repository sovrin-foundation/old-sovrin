import os

from plenum.common.pkg_util import check_deps

import sovrin

check_deps(sovrin)

from sovrin.common.plugin_helper import writeAnonCredPlugin
BASE_DIR = os.path.join(os.path.expanduser("~"), ".sovrin")
writeAnonCredPlugin(BASE_DIR)

msg = """
********************************************************************************
This package is not being developed any more.
There are three new packages which should be used instead:

sovrin-common (https://github.com/sovrin-foundation/sovrin-common)
sovrin-client (https://github.com/sovrin-foundation/sovrin-client)
sovrin-node (https://github.com/sovrin-foundation/sovrin-node)

Tickets (github issues) be logged in the appropriate new repo, but the wiki on
sovrinfoundation/sovrin (https://github.com/sovrin-foundation/sovrin/wiki) will remain active.
********************************************************************************
"""
print(msg)
