from plenum.common.log import getlogger

logger = getlogger()


def testAddSteward(nodeSet, stewardWallet, steward):
    for node in nodeSet:
        assert node.graphStore.hasSteward(stewardWallet.defaultId)


def testAddSponsor(nodeSet, addedSponsor):
    for node in nodeSet:
        assert node.graphStore.hasSponsor(addedSponsor.defaultId)
