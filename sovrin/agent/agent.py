import asyncio
from typing import Dict
from typing import Tuple

from plenum.common.error import fault
from plenum.common.exceptions import RemoteNotFound
from plenum.common.log import getlogger
from plenum.common.looper import Looper
from plenum.common.motor import Motor
from plenum.common.port_dispenser import genHa
from plenum.common.startable import Status
from plenum.common.types import Identifier
from plenum.common.util import randomString

from anoncreds.protocol.repo.attributes_repo import AttributeRepoInMemory
from sovrin.agent.agent_net import AgentNet
from sovrin.agent.caching import Caching
from sovrin.agent.walleted import Walleted
from sovrin.anon_creds.sovrin_issuer import SovrinIssuer
from sovrin.anon_creds.sovrin_prover import SovrinProver
from sovrin.anon_creds.sovrin_verifier import SovrinVerifier
from sovrin.client.client import Client
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.config_util import getConfig
from sovrin.common.identity import Identity
from sovrin.common.strict_types import strict_types, decClassMethods

logger = getlogger()


@decClassMethods(strict_types())
class Agent(Motor, AgentNet):
    def __init__(self,
                 name: str,
                 basedirpath: str,
                 client: Client = None,
                 port: int = None,
                 loop=None):
        Motor.__init__(self)
        self.loop = loop or asyncio.get_event_loop()
        self._eventListeners = {}  # Dict[str, set(Callable)]
        self._name = name
        self._port = port

        AgentNet.__init__(self,
                          name=self._name.replace(" ", ""),
                          port=port,
                          basedirpath=basedirpath,
                          msgHandler=self.handleEndpointMessage)

        # Client used to connect to Sovrin and forward on owner's txns
        self._client = client  # type: Client

        # known identifiers of this agent's owner
        self.ownerIdentifiers = {}  # type: Dict[Identifier, Identity]

    @property
    def client(self):
        return self._client

    @client.setter
    def client(self, client):
        self._client = client

    @property
    def name(self):
        return self._name

    @property
    def port(self):
        return self._port

    async def prod(self, limit) -> int:
        c = 0
        if self.get_status() == Status.starting:
            self.status = Status.started
            c += 1
        if self.client:
            c += await self.client.prod(limit)
        if self.endpoint:
            c += await self.endpoint.service(limit)
        return c

    def start(self, loop):
        super().start(loop)
        if self.client:
            self.client.start(loop)
        if self.endpoint:
            self.endpoint.start()

    def _statusChanged(self, old, new):
        pass

    def onStopping(self, *args, **kwargs):
        pass

    def connect(self, network: str):
        """
        Uses the client to connect to Sovrin
        :param network: (test|live)
        :return:
        """
        raise NotImplementedError

    def syncKeys(self):
        """
        Iterates through ownerIdentifiers and ensures the keys are correct
        according to Sovrin. Updates the updated
        :return:
        """
        raise NotImplementedError

    def handleOwnerRequest(self, request):
        """
        Consumes an owner request, verifies it's authentic (by checking against
        synced owner identifiers' keys), and handles it.
        :param request:
        :return:
        """
        raise NotImplementedError

    def handleEndpointMessage(self, msg):
        raise NotImplementedError

    def ensureConnectedToDest(self, destHa, clbk, *args):
        if self.endpoint.isConnectedTo(ha=destHa):
            if clbk:
                clbk(*args)
        else:
            self.loop.call_later(.2, self.ensureConnectedToDest,
                                 destHa, clbk, *args)

    def sendMessage(self, msg, name: str = None, ha: Tuple = None):
        try:
            remote = self.endpoint.getRemote(name=name, ha=ha)
        except RemoteNotFound as ex:
            fault(ex, "Do not know {} {}".format(name, ha))
            return

        def _send(msg, remote):
            self.endpoint.transmit(msg, remote.uid)
            logger.debug("Message sent (to -> {}): {}".format(remote.ha, msg))

        if not self.endpoint.isConnectedTo(ha=remote.ha):
            self.ensureConnectedToDest(remote.ha, _send, msg, remote)
        else:
            _send(msg, remote)

    def connectToHa(self, ha):
        self.endpoint.connectTo(ha)

    def registerEventListener(self, eventName, listener):
        cur = self._eventListeners.get(eventName)
        if cur:
            self._eventListeners[eventName] = cur.add(listener)
        else:
            self._eventListeners[eventName] = {listener}

    def deregisterEventListener(self, eventName, listener):
        cur = self._eventListeners.get(eventName)
        if cur:
            self._eventListeners[eventName] = cur - set(listener)


class WalletedAgent(Walleted, Agent, Caching):
    def __init__(self,
                 name: str,
                 basedirpath: str,
                 client: Client = None,
                 wallet: Wallet = None,
                 port: int = None,
                 loop=None,
                 attrRepo=None):
        Agent.__init__(self, name, basedirpath, client, port, loop=loop)
        self._wallet = wallet or Wallet(name)
        self._attrRepo = attrRepo or AttributeRepoInMemory()
        Walleted.__init__(self)
        if self.client:
            self._initIssuerProverVerifier()

    def _initIssuerProverVerifier(self):
        self.issuer = SovrinIssuer(client=self.client, wallet=self._wallet, attrRepo=self._attrRepo)
        self.prover = SovrinProver(client=self.client, wallet=self._wallet)
        self.verifier = SovrinVerifier(client=self.client, wallet=self._wallet)

    @Agent.client.setter
    def client(self, client):
        Agent.client.fset(self, client)
        if self.client:
            self._initIssuerProverVerifier()


def createAgent(agentClass, name, wallet=None, basedirpath=None, port=None, loop=None, clientClass=Client):
    config = getConfig()

    if not wallet:
        wallet = Wallet(name)
    if not basedirpath:
        basedirpath = config.baseDir
    if not port:
        _, port = genHa()

    _, clientPort = genHa()
    client = clientClass(randomString(6),
                         ha=("0.0.0.0", clientPort),
                         basedirpath=basedirpath)

    return agentClass(basedirpath=basedirpath,
                      client=client,
                      wallet=wallet,
                      port=port,
                      loop=loop)


def runAgent(agent, looper=None, bootstrap=True):
    def doRun(looper):
        looper.add(agent)
        logger.debug("Running {} now (port: {})".format(agent.name, agent.port))
        if bootstrap:
            looper.run(agent.bootstrap())

    if looper:
        doRun(looper)
    else:
        with Looper(debug=True, loop=agent.loop) as looper:
            doRun(looper)
            looper.run()


def createAndRunAgent(agentClass, name, wallet=None, basedirpath=None,
                      port=None, looper=None, clientClass=Client, bootstrap=True):
    loop = looper.loop if looper else None
    agent = createAgent(agentClass, name, wallet, basedirpath, port, loop, clientClass)
    runAgent(agent, looper, bootstrap)
    return agent
