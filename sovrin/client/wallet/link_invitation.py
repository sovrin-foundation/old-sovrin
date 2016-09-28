import datetime
from typing import Dict

from sovrin.common.util import getNonce

from sovrin.client.wallet.claim import AvailableClaimData, ClaimDefKey, \
    ReceivedClaim, ClaimRequest


class t:
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


# TODO: Rename to Link
class Link:
    # Rename `signerIdentifier`,
    def __init__(self, name, localIdentifier, trustAnchor=None,
                 remoteIdentifier=None, remoteEndPoint=None, nonce=None,
                 claimRequests=None, invitationData: Dict=None):
        self.name = name
        self.localIdentifier = localIdentifier

        self.trustAnchor = trustAnchor
        self.remoteIdentifier = remoteIdentifier
        self.remoteEndPoint = remoteEndPoint
        self.nonce = nonce or getNonce()
        # TODO: Keep the whole invitation data, including signature
        # self.signature = signature
        self.claimRequests = claimRequests
        self.invitationData = invitationData
        self.verkey = self.localIdentifier.split(":")[-1]
        # self.signerVerKey = signerVerKey

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

    # TODO: THis method is not used any more. We should remove it
    @staticmethod
    def getFromDict(name, values):
        localIdentifier = values[t.SIGNER_IDENTIFIER]
        trustAnchor = values[t.TRUST_ANCHOR]
        remoteIdentifier = values[t.TARGET_IDENTIFIER]
        linkNonce = values[t.LINK_NONCE]
        # signature = values[t.SIGNATURE]

        claimRequestJson = values.get(t.CLAIM_REQUESTS, None)
        claimRequests = []
        if claimRequestJson:
            for cr in claimRequestJson:
                claimRequests.append(
                    ClaimRequest(cr.get("name"), cr.get("version"),
                                 cr.get("attributes")))

        availableClaimsJson = values.get(t.AVAILABLE_CLAIMS, None)
        availableClaims = []
        if availableClaimsJson:
            for ac in availableClaimsJson:
                availableClaims.append(
                    AvailableClaimData(
                        ClaimDefKey(ac.get("name"), ac.get("version"),
                        ac.get("claimDefSeqNo"))))

        receivedClaimsJson = values.get(t.RECEIVED_CLAIMS, None)
        receivedClaims = []
        if receivedClaimsJson:
            for ac in receivedClaimsJson:
                rc = ReceivedClaim(
                        ClaimDefKey(ac.get("name"), ac.get("version"),
                                    ac.get("claimDefSeqNo")),
                        ac.get('issuerKeys'), ac.get('values'))
                rc.updateDateOfIssue(ac.get('dateOfIssue'))
                receivedClaims.append(rc)

        localVerKey = values.get(t.SIGNER_VER_KEY, None)
        remoteEndPoint = values.get(t.TARGET_END_POINT, None)

        remoteVerKey = values.get(t.TARGET_VER_KEY, None)
        linkStatus = values.get(t.LINK_STATUS, None)
        linkLastSynced = values.get(t.LINK_LAST_SYNCED, None)
        linkLastSyncNo = values.get(t.LINK_LAST_SEQ_NO, None)

        li = Link(name, localIdentifier, localVerKey, trustAnchor,
                  remoteIdentifier, remoteEndPoint, linkNonce,
                  claimRequests)
        li.updateState(remoteVerKey, linkStatus, linkLastSynced, linkLastSyncNo)
        li.updateAvailableClaims(availableClaims)

        return li

    @staticmethod
    # TODO: Create a key property for ClaimDefKey
    def _getClaimDefKeyTuple(claimDefKey: ClaimDefKey):
        return claimDefKey.name, claimDefKey.version, claimDefKey.claimDefSeqNo

    def updateReceivedClaims(self, rcvdClaims):
        for rc in rcvdClaims:
            self.receivedClaims[
                self._getClaimDefKeyTuple(rc.defKey)] = rc

    def updateAvailableClaims(self, availableClaims):
        for ac in availableClaims:
            self.availableClaims[
                self._getClaimDefKeyTuple(ac.claimDefKey)] = ac

    # TODO: THis method is not used any more. We should remove it
    def getDictToBeStored(self) -> dict:
        fixed = {
            t.SIGNER_IDENTIFIER: self.localIdentifier,
            t.TRUST_ANCHOR: self.trustAnchor,
            t.TARGET_IDENTIFIER: self.remoteIdentifier,
            t.LINK_NONCE: self.nonce,
            t.SIGNATURE: self.signature
        }
        optional = {}
        if self.verkey:
            optional[t.SIGNER_VER_KEY] = self.verkey
        if self.targetVerkey:
            optional[t.TARGET_VER_KEY] = self.targetVerkey
        if self.remoteEndPoint:
            optional[t.TARGET_END_POINT] = self.remoteEndPoint
        if self.linkStatus:
            optional[t.LINK_STATUS] = self.linkStatus
        if self.linkLastSynced:
            optional[t.LINK_LAST_SYNCED] = self.linkLastSynced.isoformat()
        if self.linkLastSyncNo:
            optional[t.LINK_LAST_SEQ_NO] = self.linkLastSyncNo

        if self.claimRequests:
            claimRequests = []
            for cr in self.claimRequests:
                claimRequests.append(cr.getDictToBeStored())
            optional[t.CLAIM_REQUESTS] = claimRequests

        if self.availableClaims:
            availableClaims = []
            for ac in self.availableClaims.values():
                availableClaims.append(ac.getDictToBeStored())
            optional[t.AVAILABLE_CLAIMS] = availableClaims

        if self.receivedClaims:
            receivedClaims = []
            for rc in self.receivedClaims.values():
                receivedClaims.append(rc.getDictToBeStored())
            optional[t.RECEIVED_CLAIMS] = receivedClaims

        fixed.update(optional)
        return fixed

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
            return t.LINK_NOT_SYNCHRONIZED

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

    def isAccepted(self):
        return self.linkStatus and self.linkStatus == t.LINK_STATUS_ACCEPTED

    def getLinkInfoStr(self) -> str:
        trustAnchor = self.trustAnchor or ""
        trustAnchorStatus = '(not yet written to Sovrin)'
        targetVerKey = t.UNKNOWN_WAITING_FOR_SYNC
        targetEndPoint = self.remoteEndPoint or t.UNKNOWN_WAITING_FOR_SYNC
        linkStatus = 'not verified, target verkey unknown'
        linkLastSynced = Link.prettyDate(self.linkLastSynced)

        if linkLastSynced != t.LINK_NOT_SYNCHRONIZED and \
                        targetEndPoint == t.UNKNOWN_WAITING_FOR_SYNC:
            targetEndPoint = "Not Available"

        if self.isAccepted():
            trustAnchorStatus = '(confirmed)'
            targetVerKey = t.TARGET_VER_KEY_SAME_AS_ID
            linkStatus = self.linkStatus

        # TODO: The verkey would be same as the local identifier until we
        # support key rotation
        verKey = t.SIGNER_VER_KEY_SAME_AS_ID
        # if self.signerVerKey:
        #     verKey = self.signerVerKey

        fixedLinkHeading = "Link "
        if not self.isAccepted():
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
        indentedLinkItems = t.LINK_ITEM_PREFIX.join(linkItems.splitlines())
        return fixedLinkHeading + indentedLinkItems
