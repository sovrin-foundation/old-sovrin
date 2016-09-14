TRUST_ANCHOR = "Trust Anchor"
SIGNER_IDENTIFIER = "Identifier"
SIGNER_VER_KEY = "Verification Key"

TARGET_IDENTIFIER = "Target"
TARGET_VER_KEY = "Target Verification Key"
TARGET_END_POINT = "Target endpoint"
SIGNATURE = "Signature"
CLAIM_REQUESTS = "Claim Requests"

LINK_NONCE = "Nonce"
LINK_STATUS = "Invitation status"
LINK_LAST_SYNCED = "Last Synced"
LINK_LAST_SEQ_NO = "Last Sync no"
LINK_STATUS_ACCEPTED = "Accepted"


class ClaimRequest:

    def __init__(self, name, version):
        self.name = name
        self.version = version


class LinkInvitation:

    def __init__(self, name, signerIdentifier, signerVerKey, trustAnchor,
                 targetIdentifier, targetEndPoint, linkNonce, claimRequests,
                 signature):
        self.name = name
        self.signerIdentifier = signerIdentifier

        self.trustAnchor = trustAnchor
        self.targetIdentifier = targetIdentifier
        self.targetEndPoint = targetEndPoint
        self.linkNonce = linkNonce
        self.signature = signature
        self.claimRequests = claimRequests

        self.signerVerKey = signerVerKey
        self.updateState(None, None, None, None)

    def updateState(self, targetVerKey, linkStatus, linkLastSynced, linkLastSyncNo):
        self.targetVerkey = targetVerKey
        self.linkStatus = linkStatus,
        self.linkLastSynced = linkLastSynced
        self.linkLastSyncNo = linkLastSyncNo

    @staticmethod
    def getFromDict(name, values):
        signerIdentifier = values[SIGNER_IDENTIFIER]
        trustAnchor = values[TRUST_ANCHOR]
        targetIdentifier = values[TARGET_IDENTIFIER]
        linkNonce = values[LINK_NONCE]
        signature = values[SIGNATURE]

        claimRequestJson = values.get(CLAIM_REQUESTS, None)

        claimRequests = []
        if claimRequestJson:
            for cr in claimRequestJson:
                claimRequests.append(ClaimRequest(cr.get("name"), cr.get("version")))

        signerVerKey = values.get(SIGNER_VER_KEY, None)
        targetEndPoint = values.get(TARGET_END_POINT, None)

        targetVerKey = values.get(TARGET_VER_KEY, None)
        linkStatus = values.get(LINK_STATUS, None)
        linkLastSynced = values.get(LINK_LAST_SYNCED, None)
        linkLastSyncNo = values.get(LINK_LAST_SEQ_NO, None)

        li = LinkInvitation(name, signerIdentifier, signerVerKey, trustAnchor,
                            targetIdentifier, targetEndPoint, linkNonce, claimRequests,
                            signature)
        li.updateState(targetVerKey, linkStatus, linkLastSynced, linkLastSyncNo)
        return li

    def getDictToBeStored(self) -> dict:
        fixed = {
            SIGNER_IDENTIFIER: self.signerIdentifier,
            TRUST_ANCHOR: self.trustAnchor,
            TARGET_IDENTIFIER: self.targetIdentifier,
            LINK_NONCE: self.linkNonce,
            SIGNATURE: self.signature
        }
        optional = {}
        if self.signerVerKey:
            optional[SIGNER_VER_KEY] = self.signerVerKey
        if self.targetVerkey:
            optional[TARGET_VER_KEY] = self.targetVerkey
        if self.targetEndPoint:
            optional[TARGET_END_POINT] = self.targetEndPoint
        if self.linkStatus:
            optional[LINK_STATUS] = self.linkStatus
        if self.linkLastSynced:
            optional[LINK_LAST_SYNCED] = self.linkLastSynced
        if self.linkLastSyncNo:
            optional[LINK_LAST_SEQ_NO] = self.linkLastSyncNo

        if self.claimRequests:
            claimRequests = []
            for cr in self.claimRequests:
                claimRequests.append(dict(cr))
            optional[CLAIM_REQUESTS] = claimRequests


        fixed.update(optional)
        return fixed

    def getLinkInfoStr(self) -> str:
        trustAnchorStatus = '(not yet written to Sovrin)'
        targetVerKey = '<unknown, waiting for sync>'
        targetEndPoint = self.targetEndPoint or "Not available"
        linkStatus = 'not verified, target verkey unknown'
        linkLastSynced = '<this link has not yet been synchronized>'

        if not self.linkStatus and self.linkStatus == LINK_STATUS_ACCEPTED:
            trustAnchorStatus = '(confirmed)'
            targetVerKey = '<same as target>'
            linkLastSynced = self.linkLastSynced
            linkStatus = self.linkStatus

        verKey = '<same as local identifier>'
        if self.signerVerKey:
            verKey = self.signerVerKey

        fixed = \
            '\n' \
            'Name: ' + self.name + '\n' \
            'Identifier: ' + self.signerIdentifier + '\n' \
            'Trust anchor: ' + self.trustAnchor + ' ' + trustAnchorStatus + '\n' \
            'Verification key: ' + verKey + '\n' \
            'Signing key: <hidden>' '\n' \
            'Target: ' + self.targetIdentifier + '\n' \
            'Target Verification key: ' + targetVerKey + '\n' \
            'Target endpoint: ' + targetEndPoint + '\n' \
            'Invitation nonce: ' + self.linkNonce + '\n' \
            'Invitation status: ' + linkStatus + '\n' \
            'Last synced: ' + linkLastSynced + '\n'

        optional = ""
        if self.claimRequests:
            optional = 'Claim Requests: '
            for cr in self.claimRequests:
                optional += '\n    ' + cr.name

        if self.linkLastSyncNo:
            optional += 'Last sync seq no: ' + self.linkLastSyncNo

        return fixed + optional
