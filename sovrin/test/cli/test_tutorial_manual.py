import json

import re

from sovrin.common.txn import ENDPOINT
from sovrin.test.cli.test_tutorial import poolNodesStarted, faberCLI, faberCli,\
    aliceCli


def testManual(do, be, poolNodesStarted, poolTxnStewardData, philCLI,
               connectedToTest, nymAddedOut, attrAddedOut, faberCLI,
               credDefAdded, issuerKeyAdded, aliceCLI):

    # Create steward and add nyms and endpoint atttributes of all agents
    _, stewardSeed = poolTxnStewardData
    be(philCLI)
    do('new keyring Steward', expect=['New keyring Steward created',
                                   'Active keyring set to "Steward"'])

    mapper = {'seed': stewardSeed.decode()}
    do('new key with seed {seed}', expect=['Key created in keyring Steward'],
       mapper=mapper)
    do('connect test', within=3, expect=connectedToTest)
    for nym, ep in [('FuN98eH2eZybECWkofW6A9BKJxxnTatBCopfUiNxo6ZB', '127.0.0.1:5555'),
                    ('7YD5NKn3P4wVJLesAmA1rr7sLPqW9mR1nhFdKD518k21', '127.0.0.1:6666'),
                    ('9jegUr9vAMqoqQQUEAiCBYNQDnUbTktQY9nNspxfasZW', '127.0.0.1:7777')]:
        m = {'target': nym, 'endpoint': json.dumps({ENDPOINT: ep})}
        do('send NYM dest={target} role=SPONSOR',
           within=3, expect=nymAddedOut, mapper=m)
        do('send ATTRIB dest={target} raw={endpoint}', within=3,
           expect=attrAddedOut, mapper=m)

    seqPat = re.compile("Sequence number is ([0-9]+)")

    # Start faber cli and add cred def and issuer key
    faberCli(be, do, faberCLI)
    be(faberCLI)
    do('connect test', within=3, expect=connectedToTest)
    do('send CRED_DEF name=Transcript version=1.2 type=CL keys=student_name,ssn,degree,year,status',
       within=3, expect=credDefAdded)
    m = seqPat.search(faberCLI.lastCmdOutput)
    assert m
    cdSeqNo, = m.groups()
    do(
        'send ISSUER_KEY ref={seqNo}', within=3, expect=issuerKeyAdded,
        mapper=dict(seqNo=cdSeqNo))
    aliceCli(be, do, aliceCLI)
    be(aliceCli)
