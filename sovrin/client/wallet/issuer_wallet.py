import uuid
from typing import Dict, Tuple, Iterable, Optional

from anoncreds.protocol.cred_def_secret_key import CredDefSecretKey
from anoncreds.protocol.globals import VERSION, KEYS, NAME, ATTR_NAMES
from anoncreds.protocol.issuer_secret_key import IssuerSecretKey
from anoncreds.protocol.proof_builder import ProofBuilder
from anoncreds.protocol.prover import Prover
from anoncreds.protocol.utils import generateMasterSecret, generateVPrime
from plenum.common.log import getlogger
from plenum.common.txn import TYPE
from sovrin.client.wallet.claim import ClaimProofRequest
from sovrin.client.wallet.claim_def import IssuerPubKey, ClaimDef
from sovrin.client.wallet.credential import Credential
from sovrin.common.exceptions import ClaimDefNotFound
from sovrin.common.util import getEncodedAttrs


logger = getlogger()


class IssuerWallet:
    def __init__(self, defaultClaimType=None):
        self._masterSecret = None
        self._vprimes = {}
        self._credentials = {}  # type: Dict[str, Credential]
        self._defaultClaimType = defaultClaimType

        # Attributes this wallet has from others. Think of an Prover's
        # attribute repo containing attributes from different Issuers. Key is a
        # identifier and value is a map of attributes
        self.attributesFrom = {}  # type: Dict[str, Dict]

    def createClaimDef(self, name, version, attrNames, typ=None, credDefSeqNo=None, idr=None):

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

    def _generateIssuerSecretKey(self, claimDef):
        csk = CredDefSecretKey()

        # TODO we shouldn't be storing claimdefsk, we are already storing IssuerSecretKey which holds the ClaimDefSK
        sid = self.addClaimDefSk(str(csk))

        # TODO why are we using a uuid here? The uid should be the seqNo of the pubkey in Sovrin
        isk = IssuerSecretKey(claimDef, csk, uid=str(uuid.uuid4()))
        return isk

    def createIssuerKey(self,
                        claimDefSeqNo=None,  # this or a claimDef must exist
                        claimDef=None,
                        seqNo=None,
                        identifier=None):
        idr = identifier or self.defaultId
        claimDef = claimDef or self.getClaimDef(seqNo=claimDefSeqNo)
        # TODO this code assumes the claim def is local. It should retrieve it if not found
        if not claimDef:
            raise ClaimDefNotFound(claimDefSeqNo)

        isk = self._generateIssuerSecretKey(claimDef)
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
