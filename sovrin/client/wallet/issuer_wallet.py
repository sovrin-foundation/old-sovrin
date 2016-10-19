import uuid
from typing import Dict, Tuple, Iterable, Optional

from anoncreds.protocol.cred_def_secret_key import CredDefSecretKey
from anoncreds.protocol.issuer_secret_key import IssuerSecretKey
from plenum.common.log import getlogger
from sovrin.client.wallet.claim_def import IssuerPubKey, ClaimDef
from sovrin.client.wallet.credential import Credential
from sovrin.common.exceptions import ClaimDefNotFound


logger = getlogger()


class IssuerWallet:
    def __init__(self, defaultClaimType=None):
        self._masterSecret = None
        self._vprimes = {}
        self._credentials = {}  # type: Dict[str, Credential]
        self._defaultClaimType = defaultClaimType

        # Attributes this wallet has for others. Think of an Issuer's attribute
        #  repo containing attributes for different Provers. Key is a nonce and
        #  value is a map of attributes
        self.attributesFor = {}  # type: Dict[str, Dict]

    def createClaimDef(self, name, version, attrNames, typ=None,
                       credDefSeqNo=None, idr=None):
        idr = idr or self.defaultId
        # TODO: Directly using anoncreds lib, should use plugin
        claimDef = ClaimDef(seqNo=credDefSeqNo,
                            attrNames=attrNames,
                            name=name,
                            version=version,
                            origin=idr,
                            typ=typ or self._defaultClaimType)
        self.addClaimDef(claimDef)
        return claimDef

    def _generateIssuerSecretKey(self, claimDef, csk=None):
        csk = csk or CredDefSecretKey()

        # TODO why are we using a uuid here? The uid should be the
        # seqNo of the pubkey in Sovrin
        isk = IssuerSecretKey(claimDef, csk, uid=str(uuid.uuid4()))
        return isk

    def createIssuerKey(self,
                        claimDefSeqNo=None,  # this or a claimDef must exist
                        claimDef=None,
                        seqNo=None,
                        identifier=None,
                        csk=None):
        idr = identifier or self.defaultId
        claimDef = claimDef or self.getClaimDef(seqNo=claimDefSeqNo)
        # TODO this code assumes the claim def is local. It should retrieve
        # it if not found
        if not claimDef:
            raise ClaimDefNotFound(claimDefSeqNo)

        isk = self._generateIssuerSecretKey(claimDef, csk=csk)
        self.addIssuerSecretKey(isk)

        ipk = IssuerPubKey(N=isk.PK.N, R=isk.PK.R, S=isk.PK.S, Z=isk.PK.Z,
                           claimDefSeqNo=claimDef.seqNo,
                           seqNo=seqNo,
                           origin=idr)
        self.addIssuerPublicKey(ipk)
        return ipk

    def addClaimDefSk(self, claimDefSk):
        uid = str(uuid.uuid4())
        self._claimDefSks[uid] = claimDefSk
        return uid

    def getClaimDefSk(self, claimDefSeqNo) -> Optional[IssuerSecretKey]:
        for isk in self._issuerSks.values():
            if isk.cd.seqNo == claimDefSeqNo:
                return isk.sk
