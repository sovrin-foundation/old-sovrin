
AVAILABLE_BUT_NOT_ISSUED_STATUS = "available (not yet issued)"


class ClaimProofRequest:
    def __init__(self, name, version, attributes):
        self.name = name
        self.version = version
        self.attributes = attributes

    @property
    def toDict(self):
        return {
            "name": self.name,
            "version": self.version,
            "attributes": self.attributes
        }

    @property
    def attributeValues(self):
        return \
            'Attributes:' + '\n    ' + \
            format("\n    ".join(
            ['{}: {}'.format(k, v)
             for k,v in self.attributes.items()]))

    def __str__(self):

        fixedInfo = \
            'Status: Requested' + '\n' \
            'Name: ' + self.name + '\n' \
            'Version: ' + self.version + '\n'

        return fixedInfo + self.attributeValues


class Claim:
    def __init__(self, issuerId, issuerPubKey):
        self.issuerId = issuerId
        self.issuerPubKey = issuerPubKey
