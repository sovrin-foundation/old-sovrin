from typing import Dict


class Claim:

    def __init__(self, name: str, version: str, attributes: Dict[str, str]):
        self.name = name
        self.version = version
        self.attributes = attributes

