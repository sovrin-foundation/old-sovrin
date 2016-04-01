from collections import OrderedDict

nodeReg = OrderedDict([
    ('Suncoast', ('127.0.0.1', 8001)),
    ('VACU', ('127.0.0.1', 8003)),
    ('WSECU', ('127.0.0.1', 8005)),
    ('CUSO', ('127.0.0.1', 8007))
])

cliNodeReg = OrderedDict([
    ('SuncoastC', ('127.0.0.1', 8002)),
    ('VACUC', ('127.0.0.1', 8004)),
    ('WSECUC', ('127.0.0.1', 8006)),
    ('CUSOC', ('127.0.0.1', 8008))
])

baseDataDir = "~"


logFilePath = "cli.log"
outFilePath = "cli_output.log"
