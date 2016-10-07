from sovrin.agent.endpoint import Endpoint


class AgentNet:
    """
    Mixin for Agents to encapsulate the network interface to communicate with
    other agents.
    """
    def __init__(self, name, port, basedirpath, msgHandler):
        if port:
            self.endpoint = Endpoint(port=port,
                                     msgHandler=msgHandler,
                                     name=name,
                                     basedirpath=basedirpath)
        else:
            self.endpoint = None
