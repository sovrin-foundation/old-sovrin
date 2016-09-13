from plenum.common.util import getlogger

logger = getlogger()


def testAddSteward(genned, steward):
    for node in genned:
        assert node.graphStore.hasSteward(steward.defaultIdentifier)


def testAddSponsor(genned, addedSponsor):
    for node in genned:
        assert node.graphStore.hasSponsor(addedSponsor.verstr)
