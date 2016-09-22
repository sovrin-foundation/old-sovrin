from typing import Dict


class Credential:
    def __init__(self, name: str, data: Dict):
        self.name = name
        self.data = data

    def key(self):
        return self.name