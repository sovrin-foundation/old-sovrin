from typing import Dict, Tuple, Iterable, Optional

from anoncreds.protocol.proof_builder import ProofBuilder
from anoncreds.protocol.prover import Prover
from anoncreds.protocol.utils import generateMasterSecret, generateVPrime
from plenum.common.log import getlogger
from sovrin.client.wallet.claim import ClaimProofRequest
from sovrin.client.wallet.credential import Credential
from sovrin.common.util import getEncodedAttrs


logger = getlogger()


class ProverWallet():
    def __init__(self):
        self._masterSecret = None
        self._vprimes = {}
        self._credentials = {}  # type: Dict[str, Credential]

        # Attributes this wallet has from others. Think of an Prover's
        # attribute repo containing attributes from different Issuers. Key is a
        # identifier and value is a map of attributes
        self.attributesFrom = {}  # type: Dict[str, Dict]

    @property
    def masterSecret(self):
        if not self._masterSecret:
            self._masterSecret = generateMasterSecret()
        return self._masterSecret

    def getVPrimes(self, *keys):
        return Prover.getVPrimes(self, *keys)

    def getIssuedAttributes(self, issuerId, encoded=False):
        attributes = self.attributesFrom.get(issuerId, {})
        if encoded:
            attributes = getEncodedAttrs(issuerId, attributes).get(issuerId)
        return attributes

    def addCredential(self, alias, cred: Credential):
        self._credentials[alias] = cred

    def getCredential(self, name: str):
        return self._credentials.get(name)

    def getCredentialByIssuerKey(self, seqNo: int, required=False):
        issuerPk = self.getIssuerPublicKey(seqNo=seqNo)
        if not issuerPk:
            raise RuntimeError("Cannot find issuer key with seqNo {} in wallet"
                               .format(seqNo))
        for cred in self._credentials.values():
            if cred.issuerKeyId == seqNo:
                return cred
        if required:
            raise RuntimeError("Credential not found in wallet for issuer key"
                               " {}".format(issuerPk))

    @property
    def credNames(self):
        return self._credentials.keys()

    def buildClaimProof(self, nonce, cpr: ClaimProofRequest):
        # Assuming building proof from a single claim
        attrNames = set(cpr.attributes.keys())
        matchedAttrs = set()
        issuerAttrs = {}
        for iid, attributes in self.attributesFrom.items():
            lookingFor = attrNames - matchedAttrs
            commonAttrs = lookingFor.intersection(set(attributes.keys()))
            issuerAttrs[iid] = commonAttrs
            matchedAttrs.update(commonAttrs)
            if len(matchedAttrs) == len(attrNames):
                break

        creds = {}
        issuerPks = {}
        encodedAttrs = {}
        claimDefKeys = {}
        revealedAttrs = []

        # Use credential for each each issuer's attributes
        for issuerId, attrs in issuerAttrs.items():
            # Get issuer key for these `attrs`
            # Then get credential for that issuer key
            for uid, ipk in self._issuerPks.items():
                if ipk.canBeUsedForAttrsFrom(issuerId, attrs):
                    issuerPks[issuerId] = ipk
                    creds[issuerId] = self.getCredentialByIssuerKey(
                        seqNo=ipk.seqNo).toNamedTuple
                    claimDef = self.getClaimDef(seqNo=ipk.claimDefSeqNo)
                    claimDefKeys[issuerId] = list(claimDef.key)
                    revealedAttrs.extend(list(attrs))
                    encodedAttrs.update(getEncodedAttrs(issuerId,
                                                        self.attributesFrom[issuerId]))

        # REMOVE-LOG: Remove the next log
        logger.debug("issuerPks, masterSecret, creds, revealedAttrs, nonce, "
                     "encodedAttrs {} {} {} {} {} {}".format(issuerPks,
                                                             self.masterSecret,
                                                             creds,
                                                             revealedAttrs,
                                                             nonce,
                                                             encodedAttrs))
        proof = ProofBuilder.prepareProofAsDict(issuerPks=issuerPks,
                                                masterSecret=self.masterSecret,
                                                creds=creds,
                                                revealedAttrs=revealedAttrs,
                                                nonce=nonce,
                                                encodedAttrs=encodedAttrs)
        return proof, encodedAttrs, revealedAttrs, claimDefKeys

    def getUValueForIssuerKeys(self, seqNos: Optional[Iterable[int]]=None,
                               keys: Optional[Iterable[Tuple[str, int]]]=None,
                               claimDefs: Optional[Iterable[
                                   Tuple[str, Tuple[str, str, str]]]]=None):
        # 2 of the 3 args should be None
        assert (seqNos, keys, claimDefs).count(None) == 2
        if seqNos:
            count = len(seqNos)
            getter = self.getIssuerPublicKey
            args = [{'seqNo': seqNo} for seqNo in seqNos]
        elif keys:
            count = len(keys)
            getter = self.getIssuerPublicKey
            args = [{'key': key} for key in keys]
        else:
            count = len(claimDefs)
            getter = self.getIssuerPublicKeyForClaimDef
            args = [{'issuerId': iid, 'claimDefKey': cdKey} for iid, cdKey in
                    claimDefs]

        # TODO: Question: What if we have more get more than one issuer key
        # for any issuer
        issuerKeys = {}
        for arg in args:
            ipk = getter(**arg)
            if ipk:
                issuerKeys[ipk.origin] = ipk

        assert len(issuerKeys) == count, "Required {} keys but found {}".\
            format(count, len(issuerKeys))
        masterSecret = self.masterSecret
        vprime = self.getVPrimes(*tuple(issuerKeys.keys()))
        proofBuilder = ProofBuilder(issuerKeys, masterSecret, vprime=vprime)
        return proofBuilder.U
