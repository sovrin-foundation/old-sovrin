import json
import logging

from aiohttp import web
from aiohttp_sse import EventSourceResponse

from plenum.common.request_types import f
from plenum.common.startable import Status
from plenum.common.transaction_store import TransactionStore, StoreStopping


class WebServer:

    def __init__(self,
                 loop,
                 txnStore: TransactionStore,
                 host: str=None,
                 port: int=None):
        self.loop = loop
        self.txnStore = txnStore
        self.app = None
        self.handler = None
        self.srv = None
        self.host = host if host else "127.0.0.1"
        self.port = port if port else 8080
        self.status = Status.stopped

    async def txn_result_stream_handler(self, request):
        get_data = request.GET
        client_id = get_data['client_id']

        resp = EventSourceResponse()
        resp.start(request)

        try:
            while True:
                txn_data = await self.txnStore.get_all_txn(client_id)
                resp.send(json.dumps(txn_data))
        except StoreStopping:
            logging.debug("Stopping stream handler because store is stopping.")
        except GeneratorExit:
            logging.debug("Stopping because of generator exit.")
        finally:
            resp.stop_streaming()
        return resp

    async def new_txn_handler(self, request):
        payload = await request.payload.read()
        if isinstance(payload, (bytes, bytearray)):
            payload = payload.decode('utf-8')
        cliReq = json.loads(payload)
        await self.txnStore.add_txn(cliReq)
        return web.Response(body=("Got your transaction client %s" % cliReq[f.CLIENT_ID.nm]).encode('utf-8'))

    # noinspection PyProtectedMember
    async def get_txn_handler(self, request):
        get_data = request.GET
        txnId = get_data['txn_id']
        txn = await self.txnStore.get_txn(txnId)
        resp = json.dumps(txn._asdict()) if txn is not None else "{}"
        return web.Response(body=resp.encode('utf-8'))

    async def index(self, request):
        d = b"""
            <html>
            <head>
                <script type="text/javascript"
                    src="http://code.jquery.com/jquery.min.js"></script>
                <script type="text/javascript">
                var evtSource = new EventSource("/txn_results?client_id=3");
                evtSource.onmessage = function(e) {
                 $('#response').html(e.data);
                }

                </script>
            </head>
            <body>
                <h1>Response from server:</h1>
                <div id="response"></div>
            </body>
        </html>
        """
        return web.Response(body=d)

    async def start(self):
        self.status = Status.starting
        # TODO keeping debug only till development. Use an environment variable later to check if running
        # in development mode or live
        self.app = web.Application(loop=self.loop, debug=True)

        self.app.router.add_route('POST', '/transaction', self.new_txn_handler)

        # TODO Make them rest urls
        self.app.router.add_route("GET", "/txn_results", self.txn_result_stream_handler)
        self.app.router.add_route('GET', '/transaction', self.get_txn_handler)

        self.app.router.add_route('GET', '/index', self.index)

        self.handler = self.app.make_handler()
        self.srv = await self.loop.create_server(self.handler, self.host, self.port)
        logging.info("Server started at http://%s:%s" % (self.host, self.port))
        self.status = Status.started

    async def stop(self):
        if self.status in (Status.stopping, Status.stopped):
            raise RuntimeError("webserver is already {}".format(self.status.name))
        self.status = Status.stopping
        await self.handler.finish_connections(3.0)
        if self.srv:
            self.srv.close()
            await self.srv.wait_closed()
        await self.app.finish()
        self.status = Status.stopped
