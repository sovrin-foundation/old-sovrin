def createAvailClaimListMsg(identifier):
    return {
                "type":"AVAIL_CLAIM_LIST",
                "identifier": "<identifier>",
                "claimsList": [ {
                    "name": "Transcript",
                    "version": "1.2",
                    "claimDefSeqNo":" <claimDefSeqNo>",
                    "definition": {
                        "attributes": {
                            "student_name": "string",
                            "ssn": "int",
                            "degree": "string",
                            "year": "string",
                            "status": "string"
                        }
                    }
                } ]
              }
