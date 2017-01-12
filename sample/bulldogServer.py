# Used to run an http server that allows downloading of invitation files
from socketserver import TCPServer
from urllib.parse import urlparse, parse_qs
from http.server import SimpleHTTPRequestHandler
from json import load

from sovrin.test.agent.bulldog_helper import bulldogLogger


PORT = 8182


logger = bulldogLogger


class BulldogServer(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsedResult = urlparse(self.path)
        fileToDownload = parsedResult.path.split('/')[-1]
        account = parse_qs(parsedResult.query)['account']
        try:
            with open(fileToDownload) as file:
                invitation = load(file)
                link = invitation['link-invitation']
                logger.info('New link invitation for account {}'.format(account))
                logger.info('Generated nonce {}'.format(link['nonce']))
                logger.info('Signed invitation with signature {}'
                            .format(invitation['sig']))
                logger.info('Invitation downloaded successful')
        except IOError as ex:
            logger.info('IOError occurred {}'.format(ex))
        return super().do_GET()


# There is some issue with enclosing below statement inside `with`
httpd = TCPServer(('', PORT), BulldogServer)
print('serving at port', PORT)
try:
    httpd.serve_forever()
except KeyboardInterrupt:
    httpd.server_close()
    print('Goodbye! Stopped bulldog server.')

# sample command to run
# $ python -m bulldogServer.py
# switch to another directory where we need to download invitation file
# if we fire wget command in same sample directory, then we would have
# two invitations with name as -1 or -2 appended
