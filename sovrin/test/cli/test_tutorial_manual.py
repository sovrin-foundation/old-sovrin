import json

import re

from plenum.common.port_dispenser import genHa

from sovrin.common.txn import ENDPOINT
from sovrin.test.agent.faber import FaberAgent
from sovrin.test.cli.test_tutorial import poolNodesStarted, faberCLI, faberCli as createFaberCli, aliceCli as createAliceCli, acmeCLI, acmeCli as createAcmeCli


def getSeqNoFromCliOutput(cli):
    seqPat = re.compile("Sequence number is ([0-9]+)")
    m = seqPat.search(cli.lastCmdOutput)
    assert m
    seqNo, = m.groups()
    return seqNo


def testManual(do, be, poolNodesStarted, poolTxnStewardData, philCLI,
               connectedToTest, nymAddedOut, attrAddedOut, faberCLI,
               credDefAdded, issuerKeyAdded, aliceCLI, newKeyringOut, aliceMap, acmeCLI):

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

    # Start Faber cli and add cred def and issuer key
    createFaberCli(be, do, faberCLI)
    be(faberCLI)
    do('connect test', within=3, expect=connectedToTest)
    do('send CRED_DEF name=Transcript version=1.2 type=CL keys=student_name,ssn,degree,year,status',
       within=3, expect=credDefAdded)
    faberCdSeqNo = getSeqNoFromCliOutput(faberCLI)
    do(
        'send ISSUER_KEY ref={seqNo}', within=3, expect=issuerKeyAdded,
        mapper=dict(seqNo=faberCdSeqNo))
    faberIkSeqNo = getSeqNoFromCliOutput(faberCLI)

    # Start Acme cli and add cred def and issuer key
    createAcmeCli(be, do, acmeCLI)
    be(acmeCLI)
    do('connect test', within=3, expect=connectedToTest)
    do(
        'send CRED_DEF name=Job-Certificate version=0.2 type=CL keys=first_name,last_name,employee_status,experience,salary_bracket',
        within=3, expect=credDefAdded)
    acmeCdSeqNo = getSeqNoFromCliOutput(acmeCLI)
    do(
        'send ISSUER_KEY ref={seqNo}', within=3, expect=issuerKeyAdded,
        mapper=dict(seqNo=acmeCdSeqNo))
    acmeIkSeqNo = getSeqNoFromCliOutput(acmeCLI)

    # Start Faber Agent and Acme Agent
    faberAgent = FaberAgent
    faberPort = genHa()[1]
    faberAgent.getPassedArgs = lambda: faberPort, int(faberCdSeqNo), \
                               int(faberIkSeqNo)

    # Start Alice cli
    createAliceCli(be, do, aliceCLI, newKeyringOut, aliceMap)
    be(aliceCLI)
