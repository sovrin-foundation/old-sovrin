import os

from sovrin.common.config_util import getConfig

#TODO: make anoncreds pluggable

def writeAnonCredPlugin(baseDir, reloadTestModules: bool = False):
    config = getConfig()
    pluginsPath = os.path.expanduser(os.path.join(baseDir, config.PluginsDir))

    if not os.path.exists(pluginsPath):
        os.makedirs(pluginsPath)

    initFile = pluginsPath + "/__init__.py"
    with open(initFile, "a"):
        pass

    modules_to_reload = ["sovrin.cli.cli"]
    test_modules_to_reload = [
        "sovrin.test.helper", "sovrin.test.cli.helper"
        # "sovrin.test.anon_creds.anon_creds_demo"
    ]

    if reloadTestModules:
        modules_to_reload.extend(test_modules_to_reload)

    reload_module_code = \
        "reload_modules = " + str(modules_to_reload) + "\n" \
                                                       "for m in reload_modules:\n" \
                                                       "   try:\n" \
                                                       "       module_obj = importlib.import_module(m)\n" \
                                                       "       importlib.reload(module_obj)\n" \
                                                       "   except AttributeError as ae:\n" \
                                                       "       print(\"Plugin loading failed: module {}, detail: {}\".format(m, str(ae)))\n" \
                                                       "\n"
