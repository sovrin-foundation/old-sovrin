
AVAILABLE_BUT_NOT_ISSUED_STATUS = "available (not yet issued)"


class ClaimRequest:
    def __init__(self, name, version, attributes):
        self.name = name
        self.version = version
        self.attributes = attributes

    def getDictToBeStored(self):
        return {
            "name": self.name,
            "version" : self.version,
            "attributes": self.attributes
        }


class ClaimDefKey:
    def __init__(self, name, version, claimDefSeqNo):
        self.name = name
        self.version = version
        self.claimDefSeqNo = claimDefSeqNo


class AvailableClaimData:
    def __init__(self, claimDefKey: ClaimDefKey):
        self.claimDefKey = claimDefKey

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

    def getClaimDefInfoStr(self) -> str:
        fixedClaimDefItems = \
            'Definition:' + '\n' \
            '   Attributes:' + '\n'

        return fixedClaimDefItems + self.getAttributeValue()


class ReceivedClaim:

    def __init__(self, defKey: ClaimDefKey, issuerKeys, values):
        self.defKey = defKey
        self.issuerKeys = issuerKeys
        self.values = values

        self.dateOfIssue = AVAILABLE_BUT_NOT_ISSUED_STATUS

    def updateDateOfIssue(self, doi):
        self.dateOfIssue = doi

    def getDictToBeStored(self):
        return {
            "name": self.defKey.name,
            "version": self.defKey.version,
            "claimDefSeqNo": self.defKey.claimDefSeqNo,
            "issuerKeys": self.issuerKeys,
            "values": self.values,
            "dateOfIssue": self.dateOfIssue
        }

    def getAttributeValue(self):
        return format("\n      ".join(
            ['{}: {}'.format(k, v)
             for k, v in self.values.items()]))

    def getClaimInfoStr(self) -> str:
        fixedClaimItems = \
            '\n' \
            'Name: ' + self.defKey.name + '\n' \
            'Version: ' + self.defKey.version + '\n' \
            'Status: ' + self.dateOfIssue + '\n' \
            'Definition: ' + '\n' \
            '   Attributes: ' + '\n'

        return fixedClaimItems + self.getAttributeValue()
