
class ClaimDefKey:
    def __init__(self, name, version, defProviderIdr):
        self.name = name
        self.version = version
        self.defProviderIdr = defProviderIdr


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
            'Definition: ' + '\n' \
            '   Attributes: ' + '\n'

        return fixedClaimDefItems + self.getAttributeValue()


class Claim:
    def __init__(self, key: ClaimDefKey, issuerIdr, issuerKeys, value):
        self.key = key
        self.issuerIdr = issuerIdr
        self.issuerKeys = issuerKeys
        self.value = value

    def updateDateOfIssue(self, doi):
        self.dateOfIssue = doi

    def getDictToBeStored(self):
        return {
            "name": self.key.name,
            "version": self.key.version,
            "defProviderIdr": self.key.defProviderIdr,
            "issuerKeys": self.issuerKeys,
            "value": self.value,
            "dateOfIssuer": self.dateOfIssue
        }

    def getAttributeWithValue(self):
        return "<TBD>"

    def getClaimInfoStr(self) -> str:
        fixedClaimItems = \
            '\n' \
            'Name: ' + self.key.name + '\n' \
            'Version: ' + self.key.version + '\n' \
            'Status: ' + self.dateOfIssue + '\n' \
            'Definition: ' + '\n' \
            '   Attributes: ' + '\n'

        return fixedClaimItems + self.getAttributeWithValue()
