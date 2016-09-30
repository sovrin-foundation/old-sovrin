import datetime
from typing import Dict

from sovrin.common.util import getNonce


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
                 claimRequests=None, invitationData: Dict=None):
        self.name = name
        self.localIdentifier = localIdentifier
        self.verkey = self.localIdentifier.split(":")[-1]

        self.trustAnchor = trustAnchor
        self.remoteIdentifier = remoteIdentifier
        self.remoteEndPoint = remoteEndPoint
        self.nonce = nonce or getNonce()
        self.claimRequests = claimRequests
        self.invitationData = invitationData

        self.availableClaims = {}
        self.receivedClaims = {}
        self.targetVerkey = None
        self.linkStatus = None
        self.linkLastSynced = None
        self.linkLastSyncNo = None

    def updateState(self, targetVerKey, linkStatus, linkLastSynced,
                    linkLastSyncNo):
        self.targetVerkey = targetVerKey
        self.linkStatus = linkStatus
        self.linkLastSynced = datetime.datetime.strptime(
            linkLastSynced, "%Y-%m-%dT%H:%M:%S.%f") \
            if linkLastSynced else None
        self.linkLastSyncNo = linkLastSyncNo

    def updateReceivedClaims(self, rcvdClaims):
        for rc in rcvdClaims:
            self.receivedClaims[rc.defKey.key] = rc

    def updateAvailableClaims(self, availableClaims):
        for ac in availableClaims:
            self.availableClaims[ac.claimDefKey.key] = ac

    @property
    def isRemoteEndpointAvailable(self):
        return self.remoteEndPoint and self.remoteEndPoint != constant.NOT_AVAILABLE

    @staticmethod
    def prettyDate(time=False):
        """
        Get a datetime object or a int() Epoch timestamp and return a
        pretty string like 'an hour ago', 'Yesterday', '3 months ago',
        'just now', etc
        """
        from datetime import datetime
        now = datetime.now()
        if time is None:
            return constant.LINK_NOT_SYNCHRONIZED

        if not isinstance(time, (int, datetime)):
            raise RuntimeError("Cannot parse time")
        if isinstance(time,int):
            diff = now - datetime.fromtimestamp(time)
        elif isinstance(time, datetime):
            diff = now - time
        else:
            diff = now - now
        second_diff = diff.seconds
        day_diff = diff.days

        if day_diff < 0:
            return ''

        if day_diff == 0:
            if second_diff < 10:
                return "just now"
            if second_diff < 60:
                return str(second_diff) + " seconds ago"
            if second_diff < 120:
                return "a minute ago"
            if second_diff < 3600:
                return str(int(second_diff / 60)) + " minutes ago"
            if second_diff < 7200:
                return "an hour ago"
            if second_diff < 86400:
                return str(int(second_diff / 3600)) + " hours ago"
        if day_diff == 1:
            return "Yesterday"
        if day_diff < 7:
            return str(day_diff) + " days ago"

    @property
    def isAccepted(self):
        return self.linkStatus == constant.LINK_STATUS_ACCEPTED

    def __str__(self):
        trustAnchor = self.trustAnchor or ""
        trustAnchorStatus = '(not yet written to Sovrin)'
        targetVerKey = constant.UNKNOWN_WAITING_FOR_SYNC
        targetEndPoint = self.remoteEndPoint or constant.UNKNOWN_WAITING_FOR_SYNC
        linkStatus = 'not verified, target verkey unknown'
        linkLastSynced = Link.prettyDate(self.linkLastSynced)

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
        # if self.signerVerKey:
        #     verKey = self.signerVerKey

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
            'Target: ' + self.remoteIdentifier + '\n' \
            'Target Verification key: ' + targetVerKey + '\n' \
            'Target endpoint: ' + targetEndPoint + '\n' \
            'Invitation nonce: ' + self.nonce + '\n' \
            'Invitation status: ' + linkStatus + '\n' \
            'Last synced: ' + linkLastSynced + '\n'

        optionalLinkItems = ""
        if len(self.claimRequests) > 0:
            optionalLinkItems += "Claim Requests: {}". \
                format(",".join([cr.name for cr in self.claimRequests]))

        if len(self.availableClaims) > 0:
            optionalLinkItems += "Available claims: {}".\
                format(",".join([ac.claimDefKey.name
                                 for ac in self.availableClaims.values()]))

        if self.linkLastSyncNo:
            optionalLinkItems += 'Last sync seq no: ' + self.linkLastSyncNo

        linkItems = fixedLinkItems + optionalLinkItems
        indentedLinkItems = constant.LINK_ITEM_PREFIX.join(linkItems.splitlines())
        return fixedLinkHeading + indentedLinkItems
