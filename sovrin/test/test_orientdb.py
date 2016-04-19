from plenum.common.util import getlogger

logger = getlogger()

def testAddSteward (nodeSet, genned, steward) :
    for node in nodeSet:
        assert node.graphStorage.hasSteward(steward.defaultIdentifier)

def testAddSponsor (nodeSet, genned, addedSponsor):
    for node in nodeSet:
        assert node.graphStorage.hasSponsor(addedSponsor.verstr)