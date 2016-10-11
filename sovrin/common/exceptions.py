class GraphDBNotPresent(Exception):
    reason = 'Install and then configure a Graph Database'


class InvalidLinkException(Exception):
    pass


class NotFound(RuntimeError):
    pass


class LinkNotFound(NotFound):
    pass


class RemoteEndpointNotFound(NotFound):
    pass


class LinkAlreadyExists(RuntimeError):
    pass


class NotConnectedToNetwork(RuntimeError):
    pass
