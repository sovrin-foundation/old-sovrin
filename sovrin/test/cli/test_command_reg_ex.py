import pytest
from prompt_toolkit.contrib.regular_languages.compiler import compile
from plenum.cli.helper import getUtilGrams, getNodeGrams, getClientGrams, getAllGrams
from plenum.test.cli.test_command_reg_ex import getMatchedVariables
from sovrin.cli.helper import getNewClientGrams


@pytest.fixture("module")
def grammar():
    grams = getClientGrams() + getNewClientGrams()
    return compile("".join(grams))


def test_send_attrib_reg_ex(grammar):
    getMatchedVariables(grammar, 'send ATTRIB dest=LNAyBZUjvLF7duhrNtOWgdAKs18nHdbJUxJLT39iEGU= raw={"legal org": "BRIGHAM YOUNG UNIVERSITY, PROVO, UT", "email":"mail@byu.edu"}')


def test_init_attr_repo_reg_ex(grammar):
    getMatchedVariables(grammar, "initialize mock attribute repo")


def test_add_attr_reg_ex(grammar):
    getMatchedVariables(grammar, "add attribute first_name=Tyler,last_name=Ruff,birth_date=12/17/1991,undergrad=True,postgrad=True,expiry_date=12/31/2101 for Tyler")


def test_add_attr_prover_reg_ex(grammar):
    getMatchedVariables(grammar, "attribute known to BYU first_name=Tyler, last_name=Ruff, birth_date=12/17/1991, undergrad=True, postgrad=True, expiry_date=12/31/2101")


def test_req_cred_reg_ex(grammar):
    getMatchedVariables(grammar,
                   "request credential Degree version 1.0 from o7NzafnAlkhNaEM5njaH+I7Y19BEbEORmFB13p87zhM= for Tyler")
    getMatchedVariables(grammar,
                        "request credential Degree version 1.0 from utNKIOcuy796g3jc+cQclAYn2/NUWRtyy/4q+EvZqQM= for Tyler")


def test_gen_cred_reg_ex(grammar):
    getMatchedVariables(grammar, "generate credential for Tyler for Degree version 1.0 with uvalue")


def test_store_cred_reg_ex(grammar):
    getMatchedVariables(grammar, "store credential A=avalue, e=evalue, vprimeprime=vprimevalue for credential cred-id as tyler-degree")


def test_list_cred_reg_ex(grammar):
    getMatchedVariables(grammar, "list CRED")


def test_gen_verif_nonce_reg_ex(grammar):
    getMatchedVariables(grammar, "generate verification nonce")


def test_prep_proof_reg_ex(grammar):
    getMatchedVariables(grammar, "prepare proof of degree using nonce mynonce for undergrad")


def test_verify_proof_reg_ex(grammar):
    getMatchedVariables(grammar, "verify status is undergrad in proof degreeproof")
