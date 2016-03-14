import asyncio
import logging
from asyncio import BaseEventLoop

from sovirin.agent import rest_server
from plenum.common.exceptions import PortNotAvailableForNodeWebServer
from plenum.common.transaction_store import TransactionStore
from plenum.common.util import getRandomPortNumber


class HasWebserver:
    def __init__(self, txnStore: TransactionStore, loop: BaseEventLoop=None):
        self.txnStore = txnStore
        self.loop = loop if loop else asyncio.get_event_loop()
        self.host = "0.0.0.0"
        # only for running all the nodes on a single machine.
        # try to create web-server on a randomly selected port. Retry 3 times if port not available
        self.port = getRandomPortNumber()
        self.webserverFut = None
        i = 0
        while i < 3:
            try:
                self.webserver = rest_server.WebServer(self.loop,
                                                       self.txnStore,
                                                       self.host,
                                                       self.port)
                logging.debug("Web-server would listen at {}:{}".format(self.host, self.port))
                break
            except OSError:
                self.port = getRandomPortNumber()
                i += 1
        else:
            raise PortNotAvailableForNodeWebServer
        self.isWebServerStarted = False

    def startWebserver(self):
        self.webserverFut = self.loop.create_task(self.webserver.start())
        self.isWebServerStarted = True

    def stopWebserver(self):
        if self.loop.is_running():
            self.loop.create_task(self.webserver.stop())
        else:
            self.loop.run_until_complete(self.webserver.stop())
        self.isWebServerStarted = False
