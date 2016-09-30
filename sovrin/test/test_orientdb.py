from plenum.common.log import getlogger

logger = getlogger()


def testAddSteward(genned, stewardWallet, steward):
    for node in genned:
        assert node.graphStore.hasSteward(stewardWallet.defaultId)


def testAddSponsor(genned, addedSponsor):
    for node in genned:
        assert node.graphStore.hasSponsor(addedSponsor.defaultId)
