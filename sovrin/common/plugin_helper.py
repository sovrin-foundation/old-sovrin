
import os
from sovrin.common.util import getConfig


def writeAnonCredPlugin(baseDir, reloadTestClasses:bool = False):
    config = getConfig()
    pluginsPath = os.path.expanduser(os.path.join(baseDir, config.PluginsDir))

    if not os.path.exists(pluginsPath):
        os.makedirs(pluginsPath)

    initFile = pluginsPath + "/__init__.py"
    with open(initFile, "a"):
        pass

    anonPluginFilePath = pluginsPath + "/anoncreds.py"
    anonPluginContent = "" \
                        "import importlib\n" \
                        "import anoncreds.protocol.issuer\n" \
                        "import sovrin.anon_creds.issuer\n" \
                        "from sovrin.client.client import Client\n" \
                        "\n" \
                        "Name = \"Anon creds\"\n" \
                        "Version = 1.1\n" \
                        "SovrinVersion = 2.1\n" \
                        "\n" \
                        "sovrin.anon_creds.issuer.Issuer = " \
                        "anoncreds.protocol.issuer.Issuer\n" \
                        "importlib.reload(sovrin.client.client)\n" \
                        "importlib.reload(sovrin.test.helper)\n"

    if reloadTestClasses:
        anonPluginContent = "" \
            "" + anonPluginContent + "" \
            "importlib.reload(sovrin.test.helper)\n"

    with open(anonPluginFilePath, "a") as myfile:
        myfile.write(anonPluginContent)
