from typing import Dict

from plenum.common.txn import NAME, NONCE
from plenum.common.types import f
from plenum.common.util import prettyDate
from sovrin.common.exceptions import InvalidLinkException
from sovrin.common.util import getNonce, verifySig, getMsgWithoutSig


class constant:
    TRUST_ANCHOR = "Trust Anchor"
    SIGNER_IDENTIFIER = "Identifier"
    SIGNER_VER_KEY = "Verification Key"
    SIGNER_VER_KEY_SAME_AS_ID = '<same as local identifier>'

    TARGET_IDENTIFIER = "Target"
    TARGET_VER_KEY = "Target Verification Key"
    TARGET_VER_KEY_SAME_AS_ID = '<same as target>'
    TARGET_END_POINT = "Target endpoint"
    SIGNATURE = "Signature"
    CLAIM_REQUESTS = "Claim Requests"
    AVAILABLE_CLAIMS = "Available Claims"
    RECEIVED_CLAIMS = "Received Claims"

    LINK_NONCE = "Nonce"
    LINK_STATUS = "Invitation status"
    LINK_LAST_SYNCED = "Last Synced"
    LINK_LAST_SEQ_NO = "Last Sync no"
    LINK_STATUS_ACCEPTED = "Accepted"

    LINK_NOT_SYNCHRONIZED = "<this link has not yet been synchronized>"
    UNKNOWN_WAITING_FOR_SYNC = "<unknown, waiting for sync>"

    LINK_ITEM_PREFIX = '\n\t'

    NOT_AVAILABLE = "Not Available"


class Link:
    def __init__(self, name, localIdentifier, trustAnchor=None,
                 remoteIdentifier=None, remoteEndPoint=None, nonce=None,
                 claimProofRequests=None, invitationData: Dict=None):
        self.name = name
        self.localIdentifier = localIdentifier
        self.verkey = self.localIdentifier.split(":")[-1]

        self.trustAnchor = trustAnchor
        self.remoteIdentifier = remoteIdentifier
        self.remoteEndPoint = remoteEndPoint
        self.nonce = nonce or getNonce()
        self.invitationData = invitationData

        self.claimProofRequests = claimProofRequests or []
        self.availableClaims = []
        self.targetVerkey = None
        self.linkStatus = None
        self.linkLastSynced = None
        self.linkLastSyncNo = None

    def __repr__(self):
        return self.key

    @property
    def key(self):
        return self.name

    @property
    def isRemoteEndpointAvailable(self):
        return self.remoteEndPoint and self.remoteEndPoint != \
                                       constant.NOT_AVAILABLE

    @property
    def isAccepted(self):
        return self.linkStatus == constant.LINK_STATUS_ACCEPTED

    def __str__(self):
        trustAnchor = self.trustAnchor or ""
        trustAnchorStatus = '(not yet written to Sovrin)'
        targetVerKey = constant.UNKNOWN_WAITING_FOR_SYNC
        targetEndPoint = self.remoteEndPoint or \
                         constant.UNKNOWN_WAITING_FOR_SYNC
        linkStatus = 'not verified, target verkey unknown'
        linkLastSynced = prettyDate(self.linkLastSynced) or \
                         constant.LINK_NOT_SYNCHRONIZED

        if linkLastSynced != constant.LINK_NOT_SYNCHRONIZED and \
                        targetEndPoint == constant.UNKNOWN_WAITING_FOR_SYNC:
            targetEndPoint = constant.NOT_AVAILABLE

        if self.isAccepted:
            trustAnchorStatus = '(confirmed)'
            targetVerKey = constant.TARGET_VER_KEY_SAME_AS_ID
            linkStatus = self.linkStatus

        # TODO: The verkey would be same as the local identifier until we
        # support key rotation
        verKey = constant.SIGNER_VER_KEY_SAME_AS_ID
        fixedLinkHeading = "Link "
        if not self.isAccepted:
            fixedLinkHeading += "(not yet accepted)"

        # TODO: Refactor to use string interpolation

        fixedLinkItems = \
            '\n' \
            'Name: ' + self.name + '\n' \
            'Identifier: ' + self.localIdentifier + '\n' \
            'Trust anchor: ' + trustAnchor + ' ' + trustAnchorStatus + '\n' \
            'Verification key: ' + verKey + '\n' \
            'Signing key: <hidden>' '\n' \
            'Target: ' + (self.remoteIdentifier or
                          constant.UNKNOWN_WAITING_FOR_SYNC) + '\n' \
            'Target Verification key: ' + targetVerKey + '\n' \
            'Target endpoint: ' + targetEndPoint + '\n' \
            'Invitation nonce: ' + self.nonce + '\n' \
            'Invitation status: ' + linkStatus + '\n'

        optionalLinkItems = ""
        if len(self.claimProofRequests) > 0:
            optionalLinkItems += "Claim Requests: {}". \
                format(",".join([cr.name for cr in self.claimProofRequests]))

        if self.availableClaims:
            optionalLinkItems += "Available claims: {}".\
                format(",".join([name
                                 for name, _, _ in self.availableClaims]))

        if self.linkLastSyncNo:
            optionalLinkItems += 'Last sync seq no: ' + self.linkLastSyncNo

        fixedEndingLines = \
            '\n' \
            'Last synced: ' + linkLastSynced

        linkItems = fixedLinkItems + optionalLinkItems + fixedEndingLines
        indentedLinkItems = constant.LINK_ITEM_PREFIX.join(
            linkItems.splitlines())
        return fixedLinkHeading + indentedLinkItems

    @staticmethod
    def validate(invitationData):

        def checkIfFieldPresent(msg, searchInName, fieldName):
            if not msg.get(fieldName):
                raise InvalidLinkException(
                    "Field not found in {}: {}".format(searchInName, fieldName))

        checkIfFieldPresent(invitationData, 'given input', 'sig')
        checkIfFieldPresent(invitationData, 'given input', 'link-invitation')
        linkInvitation = invitationData.get("link-invitation")
        linkInvitationReqFields = [f.IDENTIFIER.nm, NAME, NONCE]
        for fn in linkInvitationReqFields:
            checkIfFieldPresent(linkInvitation, 'link-invitation', fn)
