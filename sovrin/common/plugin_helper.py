
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
                        "\n" \
                        "import anoncreds.protocol.issuer\n" \
                        "import sovrin.anon_creds.issuer\n" \
                        "import sovrin.cli.cli\n" \
                        "\n" \
                        "Name = \"Anon creds\"\n" \
                        "Version = 1.1\n" \
                        "SovrinVersion = 1.1\n" \
                        "\n" \
                        "sovrin.anon_creds.issuer.Issuer = anoncreds.protocol.issuer.Issuer\n" \
                        "sovrin.anon_creds.prover.Prover = anoncreds.protocol.prover.Prover\n" \
                        "sovrin.anon_creds.verifier.Verifier = anoncreds.protocol.verifier.Verifier\n" \
                        "sovrin.anon_creds.proof_builder.ProofBuilder = anoncreds.protocol.proof_builder.ProofBuilder\n" \
                        "\n" \
                        "importlib.reload(sovrin.client.client)\n" \
                        "importlib.reload(sovrin.cli.cli)\n"


    if reloadTestClasses:
        anonPluginContent = "" \
            "" + anonPluginContent + "" \
            "importlib.reload(sovrin.test.helper)\n"

    with open(anonPluginFilePath, "a") as myfile:
        myfile.write(anonPluginContent)
