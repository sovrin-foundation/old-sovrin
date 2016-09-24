from typing import Dict


class Claim:

    def __init__(self, name: str, version: str,
                 definition: Dict[str, str]):
        self.name = name
        self.version = version
        self.definition = definition
        self.status = "available (not yet issued)"

    def updateStatus(self, newStatus):
        self.status = newStatus

    def getDictToBeStored(self):
        return {
            "status": self.status,
            "definition": self.definition
        }


    def getClaimInfoStr(self) -> str:
        fixedClaimItems = \
            '\n' \
            'Name: ' + self.name + '\n' \
            'Status: ' + self.status + '\n' \
            'Version: ' + self.version + '\n' \
            'Definition: ' + '\n' \
            '   Attributes: ' + '\n'
        attributes = format("\n      ".join(
            ['{}: {}'.format(k, v)
             for k,v in self.definition["attributes"].items()]))


        return fixedClaimItems + attributes
