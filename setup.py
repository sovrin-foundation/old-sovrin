import glob
import shutil
import sys
import os

import data
from setuptools import setup, find_packages, __version__
from pip.req import parse_requirements
from shutil import copyfile

import sample

v = sys.version_info
if sys.version_info < (3, 5):
    msg = "FAIL: Requires Python 3.5 or later, " \
          "but setup.py was run using {}.{}.{}"
    v = sys.version_info
    print(msg.format(v.major, v.minor, v.micro))
    print("NOTE: Installation failed. Run setup.py using python3")
    sys.exit(1)

# Change to ioflo's source directory prior to running any command
try:
    SETUP_DIRNAME = os.path.dirname(__file__)
except NameError:
    # We're probably being frozen, and __file__ triggered this NameError
    # Work around this
    SETUP_DIRNAME = os.path.dirname(sys.argv[0])

if SETUP_DIRNAME != '':
    os.chdir(SETUP_DIRNAME)

SETUP_DIRNAME = os.path.abspath(SETUP_DIRNAME)

METADATA = os.path.join(SETUP_DIRNAME, 'sovrin', '__metadata__.py')
# Load the metadata using exec() so we don't trigger an import of ioflo.__init__
exec(compile(open(METADATA).read(), METADATA, 'exec'))

BASE_DIR = os.path.join(os.path.expanduser("~"), ".sovrin")
CONFIG_FILE = os.path.join(BASE_DIR, "sovrin_config.py")
POOL_TXN_FILE = os.path.join(BASE_DIR, "pool_transactions_sandbox")
POOL_TXN_LOCAL_FILE = os.path.join(BASE_DIR, "pool_transactions_local")
IDENTITY_TXN_FILE = os.path.join(BASE_DIR, "transactions_sandbox")
IDENTITY_TXN_LOCAL_FILE = os.path.join(BASE_DIR, "transactions_local")

if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)


setup(
    name='sovrin',
    version=__version__,
    description='Sovrin Identity',
    long_description='Sovrin Identity',
    url='https://github.com/evernym/sovrin-priv',
    author=__author__,
    author_email='dev@evernym.us',
    license=__license__,
    keywords='Sovrin identity plenum',
    packages=find_packages(exclude=['test', 'test.*', 'docs', 'docs*']) + [
        'data', 'sample'],
    package_data={
        '': ['*.txt', '*.md', '*.rst', '*.json', '*.conf', '*.html',
             '*.css', '*.ico', '*.png', 'LICENSE', 'LEGAL', '*.sovrin']},
    include_package_data=True,
    data_files=[(
        (BASE_DIR, ['data/pool_transactions_sandbox', ])
    )],
    install_requires=['base58', 'pyorient', 'plenum', 'ledger', 'semver',
                      'anoncreds'],
    setup_requires=['pytest-runner'],
    tests_require=['pytest==3.0.2'],
    scripts=['scripts/sovrin', 'scripts/init_sovrin_raet_keep',
             'scripts/start_sovrin_node',
             'scripts/generate_sovrin_pool_transactions', 'scripts/get_keys']
)

if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'w') as f:
        msg = "# Here you can create config entries according to your " \
              "needs.\n " \
              "# For help, refer config.py in the sovrin package.\n " \
              "# Any entry you add here would override that from config " \
              "example\n"
        f.write(msg)

DATA_DIR = os.path.dirname(data.__file__)
copyfile(os.path.join(DATA_DIR, "pool_transactions_sandbox"), POOL_TXN_FILE)
copyfile(os.path.join(DATA_DIR, "pool_transactions_local"), POOL_TXN_LOCAL_FILE)
copyfile(os.path.join(DATA_DIR, "transactions_sandbox"), IDENTITY_TXN_FILE)
copyfile(os.path.join(DATA_DIR, "transactions_local"), IDENTITY_TXN_LOCAL_FILE)
SAMPLE_INVITATIONS_DIR = os.path.dirname(sample.__file__)
INVITATION_DIR = os.path.join(BASE_DIR, "sample")
os.makedirs(INVITATION_DIR, exist_ok=True)
files = glob.iglob(os.path.join(SAMPLE_INVITATIONS_DIR, "*.sovrin"))
for file in files:
    if os.path.isfile(file):
        shutil.copy2(file, INVITATION_DIR)
