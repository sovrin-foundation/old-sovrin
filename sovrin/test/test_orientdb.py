from plenum.common.util import getlogger

logger = getlogger()


def testAddSteward(genned, nodeSet, steward):
    for node in nodeSet:
        assert node.graphStorage.hasSteward(steward.defaultIdentifier)


def testAddSponsor(genned, nodeSet, addedSponsor):
    for node in nodeSet:
        assert node.graphStorage.hasSponsor(addedSponsor.verstr)
