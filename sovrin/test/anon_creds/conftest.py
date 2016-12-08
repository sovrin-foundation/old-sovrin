import pytest
from anoncreds.protocol.types import AttribType, AttribDef
from config.config import cmod

GVT = AttribDef('gvt',
                [AttribType('name', encode=True),
                 AttribType('age', encode=False),
                 AttribType('height', encode=False),
                 AttribType('sex', encode=True)])


