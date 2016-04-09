#! /usr/bin/env python3
import os
from sys import stdout
from os.path import dirname

from sh import tail

import sovrin
from sovrin.common.util import getConfig

curDir = os.getcwd()
config = getConfig()
outFilePath = os.path.join(curDir, config.outFilePath)

for line in tail("-f", outFilePath, _iter=True):
    print(line)
    stdout.flush()
