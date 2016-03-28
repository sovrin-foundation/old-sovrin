#! /usr/bin/env python3
import os
from sys import stdout
from os.path import dirname

import tailer
from pygtail import Pygtail
from sh import tail

import sovrin

packagePath = sovrin.__file__
outFilePath = os.path.join(dirname(dirname(packagePath)), "log/cli_output.log")

# for line in tailer.follow(open(outFilePath, "r")):
for line in tail("-f", outFilePath, _iter=True):
    print(line)
    stdout.flush()
