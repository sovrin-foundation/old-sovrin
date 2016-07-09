import pytest
from prompt_toolkit.contrib.regular_languages.compiler import compile
from plenum.cli.helper import getUtilGrams, getNodeGrams, getClientGrams, getAllGrams
from plenum.test.cli.test_command_reg_ex import checkIfMatched
from sovrin.cli.helper import getNewClientGrams


@pytest.fixture("module")
def grammar():
    grams = getClientGrams() + getNewClientGrams()
    return compile("".join(grams))


def test_req_cred_reg_ex(grammar):
    checkIfMatched(grammar, "request credential Qualifications version 1.0 from o7NzafnAlkhNaEM5njaH+I7Y19BEbEORmFB13p87zhM=")

def test_gen_cred_reg_ex(grammar):
    checkIfMatched(grammar, "generate credential credential request")
