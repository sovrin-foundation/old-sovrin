class GraphDBNotPresent(Exception):
    reason = 'Install and then configure a Graph Database'


class InvalidLinkException(Exception):
    pass


class NotFound(RuntimeError):
    pass


class LinkNotFound(NotFound):
    def __init__(self, name: str=None):
        if name:
            self.reason = "Link with name not found".format(name)


class RemoteEndpointNotFound(NotFound):
    pass


class LinkAlreadyExists(RuntimeError):
    pass


class NotConnectedToNetwork(RuntimeError):
    pass
