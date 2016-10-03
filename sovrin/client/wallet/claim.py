
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
            'Attributes:' + '\n      ' + \
            format("\n      ".join(
            ['{}: {}'.format(k, v)
             for k,v in self.attributes.items()]))

    def __str__(self):

        fixedInfo = \
            'Name: ' + self.name + '\n' \
            'Version: ' + self.version + '\n' \
            'Status: Requested' + '\n'

        return fixedInfo + self.attributeValues


class ClaimAttr:

    def __init__(self, name, version, author, seqNo, issuerId, attributes):
        self.name = name
        self.version = version
        self.author = author
        self.seqNo = seqNo
        self.issuerId = issuerId
        self.attributes = attributes
        self.dateOfIssue = AVAILABLE_BUT_NOT_ISSUED_STATUS

    @property
    def toDict(self):
        return {
            "name": self.name,
            "version": self.version,
            "claimDefSeqNo": self.seqNo,
            "author": self.author,
            "attributes": self.attributes,
            "dateOfIssue": str(self.dateOfIssue)
        }

    @property
    def attributeValues(self):
        return format("\n      ".join(
            ['{}: {}'.format(k, v)
             for k, v in self.attributes.items()]))

    def __str__(self):
        fixedClaimItems = \
            '\n' \
            'Name: ' + self.name + '\n' \
            'Version: ' + self.version + '\n' \
            'Status: ' + str(self.dateOfIssue) + '\n' \
            'Attributes: ' + '\n      '

        return fixedClaimItems + self.attributeValues
