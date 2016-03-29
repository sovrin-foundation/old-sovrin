#! /usr/bin/env python3
import os
from sys import stdout
from os.path import dirname

from sh import tail

import sovrin

packagePath = sovrin.__file__
outFilePath = os.path.join(dirname(dirname(packagePath)), "log/cli_output.log")

for line in tail("-f", outFilePath, _iter=True):
    print(line)
    stdout.flush()
