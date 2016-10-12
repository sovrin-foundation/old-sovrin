# REQUEST MSGS TO AGENT
ACCEPT_INVITE = 'ACCEPT_INVITE'
REQUEST_CLAIM = 'REQUEST_CLAIM'
CLAIM_PROOF = 'CLAIM_PROOF'

# RESPONSE MSGS FROM AGENT
AVAIL_CLAIM_LIST = 'AVAIL_CLAIM_LIST'
CLAIM = 'CLAIM'
CLAIM_PROOF_STATUS = 'CLAIM_PROOF_STATUS'
NEW_AVAILABLE_CLAIMS = "NEW_AVAILABLE_CLAIMS"

# Other
CLAIM_NAME_FIELD = "claimName"

"""
ACCEPT_INVITE
{
    "type": 'ACCEPT_INVITE',
    "identifier": <id>,
    "nonce": <nonce>,
    "signature" : <sig>
}


AVAIL_CLAIM_LIST
{
    'type': 'AVAIL_CLAIM_LIST',
    'claims_list': [
        "Name": "Transcript",
        "Version": "1.2",
        "Definition": {
            "Attributes": {
                "student_name": "string",
                "ssn": "int",
                "degree": "string",
                "year": "string",
                "status": "string"
            }
        }
    ],
    "signature" : <sig>
}

AVAIL_CLAIM_LIST
{
    'type': 'AVAIL_CLAIM_LIST',
    'claims_list': [
        "Name": "Transcript",
        "Version": "1.2",
        "Definition": {
            "Attributes": {
                "student_name": "string",
                "ssn": "int",
                "degree": "string",
                "year": "string",
                "status": "string"
            }
        }
    ],
    "signature" : <sig>
}

"""
