import logging

from os.path import expanduser, exists
from logging import getLogger

from sovrin.common.config_util import getConfig


def getBulldogLogger():
    config = getConfig()
    path = expanduser('{}'.format(config.baseDir))
    filePath = '{}/bulldog.log'.format(path)

    try:
        if not exists(filePath):
            with open(filePath, mode='a+'):
                # we just want to create a file if not exists
                # don't do anything else with file handler
                pass

        log = getLogger()
        log.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s %(message)s')
        fileHandler = logging.FileHandler(filePath, mode='a')
        fileHandler.setLevel(logging.DEBUG)
        fileHandler.setFormatter(formatter)
        log.addHandler(fileHandler)

        return log
    except OSError:
        print('Could not create log file')
        raise Exception


bulldogLogger = getBulldogLogger()
