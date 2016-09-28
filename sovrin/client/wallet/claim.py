
AVAILABLE_BUT_NOT_ISSUED_STATUS = "available (not yet issued)"


class ClaimRequest:
    def __init__(self, name, version, attributes):
        self.name = name
        self.version = version
        self.attributes = attributes

    # TODO: Rename to `toDict` and make property
    def getDictToBeStored(self):
        return {
            "name": self.name,
            "version": self.version,
            "attributes": self.attributes
        }

    def getAttributeValue(self):
        return \
            'Attributes:' + '\n      ' + \
            format("\n      ".join(
            ['{}: {}'.format(k, v)
             for k,v in self.attributes.items()]))

    # TODO: Rename to `serToStr` and make property
    def getClaimReqInfoStr(self) -> str:

        fixedInfo = \
            'Name: ' + self.name + '\n' \
            'Version: ' + self.version + '\n' \
            'Status: Requested' + '\n'

        return fixedInfo + self.getAttributeValue()


class ClaimDefKey:
    # TODO: Create a key property for ClaimDefKey
    def __init__(self, name, version, claimDefSeqNo, author):
        self.name = name
        self.version = version
        self.claimDefSeqNo = claimDefSeqNo
        self.author = author

    # TODO: Why key of a key?
    @property
    def key(self):
        return self.name, self.version, self.claimDefSeqNo, self.author


class AvailableClaimData:
    def __init__(self, claimDefKey: ClaimDefKey):
        self.claimDefKey = claimDefKey

    # TODO: Rename to `toDict` and make property
    def getDictToBeStored(self):
        return {
            "name": self.claimDefKey.name,
            "version": self.claimDefKey.version,
            "claimDefSeqNo": self.claimDefKey.claimDefSeqNo,
        }

    def getClaimInfoStr(self) -> str:
        fixedInfo = \
            'Name: ' + self.claimDefKey.name + '\n' \
            'Version: ' + self.claimDefKey.version + '\n' \
            'Status: ' + AVAILABLE_BUT_NOT_ISSUED_STATUS
        return fixedInfo


class ClaimDef:
    def __init__(self, key: ClaimDefKey, definition):
        self.key = key
        self.definition = definition

    def getAttributeValue(self):
        return format("\n      ".join(
            ['{}: {}'.format(k, v)
             for k, v in self.definition["attributes"].items()]))

    # TODO: Rename to `serToStr` and make property
    def getClaimDefInfoStr(self) -> str:
        fixedClaimDefItems = \
            'Definition:' + '\n' \
            '   Attributes:' + '\n      '

        return fixedClaimDefItems + self.getAttributeValue()


class ReceivedClaim:

    def __init__(self, defKey: ClaimDefKey, issuerKeys, values):
        self.defKey = defKey
        self.issuerKeys = issuerKeys
        self.values = values

        self.dateOfIssue = AVAILABLE_BUT_NOT_ISSUED_STATUS

    def updateDateOfIssue(self, doi):
        self.dateOfIssue = doi

    # TODO: Rename to `toDict` and make property
    def getDictToBeStored(self):
        return {
            "name": self.defKey.name,
            "version": self.defKey.version,
            "claimDefSeqNo": self.defKey.claimDefSeqNo,
            "issuerKeys": self.issuerKeys,
            "values": self.values,
            "dateOfIssue": str(self.dateOfIssue)
        }

    def getAttributeValue(self):
        return format("\n      ".join(
            ['{}: {}'.format(k, v)
             for k, v in self.values.items()]))

    # TODO: Rename to `serToStr` and make property
    def getClaimInfoStr(self) -> str:
        fixedClaimItems = \
            '\n' \
            'Name: ' + self.defKey.name + '\n' \
            'Version: ' + self.defKey.version + '\n' \
            'Status: ' + str(self.dateOfIssue) + '\n' \
            'Attributes: ' + '\n      '

        return fixedClaimItems + self.getAttributeValue()
