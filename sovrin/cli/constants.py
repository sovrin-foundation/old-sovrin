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
SEND_CRED_REG_EX = \
    "(\s* (?P<send_cred>send\s+to) \s+ (?P<dest>[a-fA-F0-9]+) \s+ (?P<saveas>saveas)? \s+? (?P<cred_name>[a-zA-Z0-9\-_]+)? \s+? REQ_CRED \s+ " \
    " name=(?P<name>[a-zA-Z0-9\-]+) \s+ version=(?P<version>[0-9\.]+) \s+ attrs=(?P<attrs>[a-zA-Z0-9,]+) \s*) "
LIST_CREDS_REG_EX = "(\s* (?P<list_cred>list\s+CRED) \s*) "
SEND_PROOF_REG_EX = \
    "(\s* (?P<send_proof>send\s+proof) \s+ of \s+ (?P<attr_name>[a-zA-Z0-9\-_]+) \s+ from \s+ (?P<cred_name>[a-zA-Z0-9\-_]+)? \s+ to \s+ " \
    " (?P<dest>[a-fA-F0-9]+) \s*) |"

SEND_NYM_FORMATTED_REG_EX = getPipedRegEx(SEND_NYM_REG_EX)
GET_NYM_FORMATTED_REG_EX = getPipedRegEx(GET_NYM_REG_EX)
ADD_ATTRIB_FORMATTED_REG_EX = getPipedRegEx(ADD_ATTRIB_REG_EX)
SEND_CRED_DEF_FORMATTED_REG_EX = getPipedRegEx(SEND_CRED_DEF_REG_EX)
SEND_CRED_FORMATTED_REG_EX = getPipedRegEx(SEND_CRED_REG_EX)
LIST_CREDS_FORMATTED_REG_EX = getPipedRegEx(LIST_CREDS_REG_EX)
SEND_PROOF_FORMATTED_REG_EX = SEND_PROOF_REG_EX
