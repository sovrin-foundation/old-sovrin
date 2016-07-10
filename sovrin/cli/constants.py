from plenum.cli.constants import CLIENT_GRAMS_CLIENT_COMMAND_REG_EX, relist, CLI_CMDS, getPipedRegEx, \
    CLIENT_GRAMS_USE_KEYPAIR_REG_EX

CLIENT_GRAMS_CLIENT_WITH_IDENTIFIER_FORMATTED_REG_EX = getPipedRegEx(
    CLIENT_GRAMS_CLIENT_COMMAND_REG_EX + "\s+ (?P<with_identifier>with\s+identifier) \s+ (?P<nym>[a-zA-Z0-9=]+) \s*")\
    .format(relist(CLI_CMDS))

CLIENT_GRAMS_CLIENT_ADD_FORMATTED_REG_EX = getPipedRegEx(
    "(\s* (?P<client>client) \s+ (?P<client_name>[a-zA-Z0-9]+) \s+ (?P<cli_action>add) \s+ (?P<role>sponsor|user) \s+ (?P<other_client_name>[a-zA-Z0-9]+) \s*)")

CLIENT_GRAMS_USE_KEYPAIR_FORMATTED_REG_EX = getPipedRegEx(CLIENT_GRAMS_USE_KEYPAIR_REG_EX)

SEND_NYM_REG_EX = "(\s* (?P<send_nym>send\s+NYM) \s+ (?P<dest>dest=)\s*(?P<dest_id>[A-Za-z0-9+=/]*) \s+ (?P<role>USER|SPONSOR|STEWARD))"

GET_NYM_REG_EX = "(\s* (?P<send_get_nym>send\s+GET_NYM) \s+ (?P<dest>dest=)\s*(?P<dest_id>[A-Za-z0-9+=/]*) \s*) "

ADD_ATTRIB_REG_EX = \
    "(\s* (?P<send_attrib>send\s+ATTRIB) \s+ dest=\s*(?P<dest_id>[a-fA-F0-9]+) \s+ raw=(?P<raw>\{\s*.*\}) \s*) "

SEND_CRED_DEF_REG_EX = \
    "(\s* (?P<send_cred_def>send\s+CRED_DEF) \s+ name=\"\s*(?P<name>[a-zA-Z0-9\s]+)\" \s+ version=\"(?P<version>[0-9\.]+)\" " \
    "\s+type=(?P<type>[a-zA-Z0-9]+) \s+ ip=(?P<ip>[0-9\.]+) \s+ port=(?P<port>[0-9]+) \s+ keys=(?P<keys>\{\s*.*\}) \s*) "

REQ_CRED_REG_EX = \
    "(\s*(?P<req_cred>request\s+credential)\s+(?P<name>[a-zA-Z0-9\-]+)" \
    "\s+version\s(?P<version>[0-9\.]+)" \
    "\s+from\s+(?P<issuer_identifier>[A-Za-z0-9+=/]*)\s*)"

LIST_CREDS_REG_EX = "(\s* (?P<list_cred>list\s+CRED) \s*) "

SEND_PROOF_REG_EX = \
    "(\s* (?P<send_proof>send\s+proof) \s+ of \s+ (?P<attr_name>[a-zA-Z0-9\-_]+) \s+ from \s+ (?P<cred_name>[a-zA-Z0-9\-_]+)? \s+ to \s+ " \
    " (?P<dest>[a-fA-F0-9]+) \s*)"

ADD_GENESIS_REG_EX = \
    "(\s*(?P<add_genesis>add \s+ genesis \s+ transaction?) \s+ (?P<type_value>[A-Z_]+) \s+ (?P<dest>dest=)\s*(?P<dest_value>[A-Za-z0-9+=/]+) \s+ (?P<txnId>txnId=)\s*(?P<txnId_value>[a-zA-Z0-9]+) \s+ (?P<role>role=)\s*(?P<role_value>USER|SPONSOR|STEWARD)\s*)"

GEN_CRED_REG_EX = \
    "(\s* (?P<gen_cred>generate \s+ credential) " \
    "\s+ (?P<gen_cred>[a-zA-Z0-9\s]+) " \
    "\s*)"

SAVE_CRED_REG_EX = \
    "(\s* (?P<save_cred>save \s+ CRED) " \
    "\s+ as=\"\s*(?P<as>[a-zA-Z0-9\s]+)\"" \
    "\s+ cred=\"\s*(?P<cred>[a-zA-Z0-9\s]+)\"" \
    "\s*)"

INIT_ATTR_REPO_REG_EX = "(\s*(?P<init_attr_repo>initialize \s+ mock \s+ attribute \s+ repo)\s*)"

ADD_ATTRS_REG_EX = "(\s*(?P<add_attrs>add \s+ attribute) \s+ (?P<attrs>[A-Za-z0-9,+=/ ]+) \s*)"



SEND_NYM_FORMATTED_REG_EX = getPipedRegEx(SEND_NYM_REG_EX)
GET_NYM_FORMATTED_REG_EX = getPipedRegEx(GET_NYM_REG_EX)
ADD_ATTRIB_FORMATTED_REG_EX = getPipedRegEx(ADD_ATTRIB_REG_EX)
SEND_CRED_DEF_FORMATTED_REG_EX = getPipedRegEx(SEND_CRED_DEF_REG_EX)
REQ_CRED_FORMATTED_REG_EX = getPipedRegEx(REQ_CRED_REG_EX)
LIST_CREDS_FORMATTED_REG_EX = getPipedRegEx(LIST_CREDS_REG_EX)
GEN_CRED_FORMATTED_REG_EX = getPipedRegEx(GEN_CRED_REG_EX)
SEND_PROOF_FORMATTED_REG_EX = getPipedRegEx(SEND_PROOF_REG_EX)
ADD_GENESIS_FORMATTED_REG_EX = getPipedRegEx(ADD_GENESIS_REG_EX)
INIT_ATTR_REPO_FORMATTED_REG_EX = getPipedRegEx(INIT_ATTR_REPO_REG_EX)
ADD_ATTRS_FORMATTED_REG_EX = ADD_ATTRS_REG_EX