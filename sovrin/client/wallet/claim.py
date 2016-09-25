
AVAILABLE_BUT_NOT_ISSUED_STATUS = "available (not yet issued)"


class ClaimDefKey:
    def __init__(self, name, version, defProviderIdr):
        self.name = name
        self.version = version
        self.defProviderIdr = defProviderIdr


class AvailableClaimData:
    def __init__(self, claimDefKey: ClaimDefKey, issuerIdr, dateOfIssue):
        self.claimDefKey = claimDefKey
        self.issuerIdr = issuerIdr
        self.dateOfIssue = dateOfIssue or AVAILABLE_BUT_NOT_ISSUED_STATUS

    def getDictToBeStored(self):
        return {
            "name": self.claimDefKey.name,
            "version" : self.claimDefKey.version,
            "defProviderIdr": self.claimDefKey.defProviderIdr,
            "issuerIdr": self.issuerIdr,
            "dateOfIssue": self.dateOfIssue
        }

    def getClaimInfoStr(self) -> str:
        fixedInfo = \
            'Name: ' + self.claimDefKey.name + '\n' \
            'Version: ' + self.claimDefKey.version + '\n' \
            'Status: ' + self.dateOfIssue
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
            '\n' \
            'Name: ' + self.key.name + '\n' \
            'Version: ' + self.key.version + '\n' \
            'Definition:' + '\n' \
            '   Attributes:' + '\n'

        return fixedClaimDefItems + self.getAttributeValue()


class Claim:
    def __init__(self, defKey: ClaimDefKey, issuerIdr, issuerKeys, value):
        self.defKey = defKey
        self.issuerIdr = issuerIdr
        self.issuerKeys = issuerKeys
        self.value = value

    def updateDateOfIssue(self, doi):
        self.dateOfIssue = doi

    def getDictToBeStored(self):
        return {
            "name": self.defKey.name,
            "version": self.defKey.version,
            "defProviderIdr": self.defKey.defProviderIdr,
            "issuerKeys": self.issuerKeys,
            "value": self.value,
            "dateOfIssuer": self.dateOfIssue
        }

    def getAttributeWithValue(self):
        return "<TBD>"

    def getClaimInfoStr(self) -> str:
        fixedClaimItems = \
            '\n' \
            'Name: ' + self.defKey.name + '\n' \
            'Version: ' + self.defKey.version + '\n' \
            'Status: ' + self.dateOfIssue + '\n' \
            'Definition: ' + '\n' \
            '   Attributes: ' + '\n'

        return fixedClaimItems + self.getAttributeWithValue()
