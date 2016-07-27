from plenum.cli.constants import CLIENT_GRAMS_CLIENT_COMMAND_REG_EX, relist, \
    CLI_CMDS, getPipedRegEx, \
    CLIENT_GRAMS_USE_KEYPAIR_REG_EX

CLIENT_GRAMS_CLIENT_WITH_IDENTIFIER_FORMATTED_REG_EX = getPipedRegEx(
    CLIENT_GRAMS_CLIENT_COMMAND_REG_EX + "\s+ (?P<with_identifier>with\s+identifier) \s+ (?P<nym>[a-zA-Z0-9=]+) \s*") \
    .format(relist(CLI_CMDS))

CLIENT_GRAMS_CLIENT_ADD_FORMATTED_REG_EX = getPipedRegEx(
    "(\s* (?P<client>client) \s+ (?P<client_name>[a-zA-Z0-9]+) \s+ (?P<cli_action>add) \s+ (?P<role>sponsor|user) \s+ (?P<other_client_name>[a-zA-Z0-9]+) \s*)")

CLIENT_GRAMS_USE_KEYPAIR_FORMATTED_REG_EX = getPipedRegEx(
    CLIENT_GRAMS_USE_KEYPAIR_REG_EX)

# TODO we can genericize the other TXN types in the same way
TXN_NYM = "(\s* (?P<{cmdName}>{cmd}\s+NYM) \s+ (?P<dest>dest=) \s* (?P<dest_id>[A-Za-z0-9+=/]*) \s+ (?P<role_key>role=) \s* (?P<role>USER|SPONSOR|STEWARD))"
SEND_NYM_REG_EX = TXN_NYM.format(cmdName='send_nym', cmd='send')
ADD_GENESIS_NYM_REG_EX = TXN_NYM.format(cmdName='add_genesis',
                                        cmd='add \s+ genesis \s+ transaction')

# ADD_GENESIS_NYM_REG_EX = '|(\s* (?P<add_genesis>add\s+genesis\s+transaction))'

# ADD_GENESIS_REG_EX = \
#     "(\s*(?P<add_genesis>add \s+ genesis \s+ transaction?) \s+ (?P<type_value>[A-Z_]+) \s+ (?P<dest>dest=)\s*(?P<dest_value>[A-Za-z0-9+=/]+) \s+ (?P<txnId>txnId=)\s*(?P<txnId_value>[a-zA-Z0-9]+) \s+ (?P<role>role=)\s*(?P<role_value>USER|SPONSOR|STEWARD)\s*)"
#

GET_NYM_REG_EX = "(\s* (?P<send_get_nym>send\s+GET_NYM) \s+ (?P<dest>dest=)\s*(?P<dest_id>[A-Za-z0-9+=/]*) \s*) "

ADD_ATTRIB_REG_EX = \
    "(\s* (?P<send_attrib>send\s+ATTRIB) \s+ dest=\s*(?P<dest_id>[A-Za-z0-9+=/]+) \s+ raw=(?P<raw>\{\s*.*\}) \s*) "

SEND_CRED_DEF_REG_EX = "(\s*(?P<send_cred_def>send\s+CRED_DEF)\s+(?P<name_key>name=)\s*(?P<name>[A-Za-z0-9-_]+)\s*(?P<version_key>version=)\s*(?P<version>[0-9.]+)\s*(?P<type_key>type=)\s*(?P<type>[A-Z0-9]+)\s*(?P<ip_key>ip=)\s*(?P<ip>[0-9.]+)\s+(?P<port_key>port=)\s*(?P<port>[0-9]+)\s+(?P<keys_key>keys=)\s*(?P<keys>[a-zA-Z-_,\s]+)\s*)"

REQ_CRED_REG_EX = \
    "(\s*(?P<req_cred>request\s+credential) " \
    "\s+ (?P<cred_name>[a-zA-Z0-9\-]+)" \
    "\s+ version \s+ (?P<version>[0-9\.]+)" \
    "\s+ from \s+ (?P<issuer_id>[A-Za-z0-9+=/]+)" \
    "\s+ for \s+ (?P<prover_id>[a-zA-Z0-9]+)" \
    "\s*)"

LIST_CREDS_REG_EX = "(\s* (?P<list_cred>list\s+CRED) \s*) "

PREP_PROOF_REG_EX = \
    "(\s*(?P<prep_proof>prepare " \
    "\s+ proof \s+ of) \s+ (?P<cred_alias>[a-zA-Z0-9-\s]+) " \
    "\s+ using \s+ nonce \s+ (?P<nonce>[a-zA-Z0-9-\s]+)" \
    "\s+ for \s+ (?P<revealed_attrs>[a-zA-Z0-9-\s]+)" \
    "\s*) "

VERIFY_PROOF_REG_EX = \
    "(\s*(?P<verif_proof>verify \s+ status \s+ is) \s+ (?P<status>[a-zA-Z0-9-\s]+) " \
    "\s+ in \s+ proof \s+ (?P<proof>.+)" \
    "\s*) "

GEN_CRED_REG_EX = \
    "(\s*(?P<gen_cred>generate\scredential)" \
    "\s+ for \s+ (?P<prover_id>[a-zA-Z0-9]+)" \
    "\s+ for \s+ (?P<cred_name>[a-zA-Z0-9]+)" \
    "\s+ version \s+ (?P<cred_version>[0-9.]+)" \
    "\s+ with \s+ (?P<u_value>[a-zA-Z0-9\s]+)" \
    "\s*)"

# STORE_CRED_REG_EX = \
#     "(\s* (?P<store_cred>store \s+ credential)" \
#     "\s+ (?P<cred>[A-Za-z0-9_,+=/ ]+)" \
#     "\s+ for (?P<cred_def>[\.A-Za-z0-9_,+=/ ]+)" \
# "\s+ as \s+ (?P<alias>[a-zA-Z0-9-\s]+)" \
# "\s*)"


STORE_CRED_REG_EX = \
    "(\s* (?P<store_cred>store \s+ credential)" \
    "\s+ (?P<cred>[A-Za-z0-9_,+=/ ]+)" \
"\s+ for \s+ credential \s+ (?P<prf_id>[a-zA-Z0-9\-]+)" \
"\s+ as \s+ (?P<alias>[a-zA-Z0-9-\s]+)" \
"\s*)"

ADD_ATTRS_PROVER_REG_EX = "(\s*(?P<add_attrs>attribute \s+ known \s+ to) \s+ (?P<issuer_id>[A-Za-z0-9+=/]+) \s+ (?P<attrs>[A-Za-z0-9_,+=/ ]+) \s*)"

INIT_ATTR_REPO_REG_EX = "(\s*(?P<init_attr_repo>initialize \s+ mock \s+ attribute \s+ repo)\s*)"

ADD_ATTRS_REG_EX = "(\s*(?P<add_attrs>add \s+ attribute) \s+ (?P<attrs>[A-Za-z0-9_,+=/ ]+) \s+ for \s+ (?P<prover_id>[a-zA-Z0-9\-_]+) \s*)"

GEN_VERIF_NONCE_REG_EX = "(\s*(?P<gen_verif_nonce>generate \s+ verification \s+ nonce)\s*)"

SEND_NYM_FORMATTED_REG_EX = getPipedRegEx(SEND_NYM_REG_EX)
GET_NYM_FORMATTED_REG_EX = getPipedRegEx(GET_NYM_REG_EX)
ADD_ATTRIB_FORMATTED_REG_EX = getPipedRegEx(ADD_ATTRIB_REG_EX)
SEND_CRED_DEF_FORMATTED_REG_EX = getPipedRegEx(SEND_CRED_DEF_REG_EX)
REQ_CRED_FORMATTED_REG_EX = getPipedRegEx(REQ_CRED_REG_EX)
LIST_CREDS_FORMATTED_REG_EX = getPipedRegEx(LIST_CREDS_REG_EX)
GEN_CRED_FORMATTED_REG_EX = getPipedRegEx(GEN_CRED_REG_EX)
ADD_GENESIS_FORMATTED_REG_EX = getPipedRegEx(ADD_GENESIS_NYM_REG_EX)
STORE_CRED_FORMATTED_REG_EX = getPipedRegEx(STORE_CRED_REG_EX)
GEN_VERIF_NONCE_FORMATTED_REG_EX = getPipedRegEx(GEN_VERIF_NONCE_REG_EX)
PREP_PROOF_FORMATTED_REG_EX = getPipedRegEx(PREP_PROOF_REG_EX)
VERIFY_PROOF_FORMATTED_REG_EX = getPipedRegEx(VERIFY_PROOF_REG_EX)
INIT_ATTR_REPO_FORMATTED_REG_EX = getPipedRegEx(INIT_ATTR_REPO_REG_EX)
ADD_ATTRS_FORMATTED_REG_EX = getPipedRegEx(ADD_ATTRS_REG_EX)
