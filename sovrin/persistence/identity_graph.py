import json
from itertools import chain

import pyorient
from functools import reduce
from typing import Dict, Optional

from ledger.util import F
from plenum.common.error import fault
from plenum.common.log import getlogger
from plenum.common.txn import TXN_TYPE, TYPE, IP, PORT, KEYS, NAME, VERSION, \
    DATA, RAW, ENC, HASH, ORIGIN, VERKEY
from plenum.common.types import f
from plenum.common.util import error
from plenum.persistence.orientdb_graph_store import OrientDbGraphStore
from sovrin.common.txn import NYM, TXN_ID, TARGET_NYM, USER, SPONSOR, \
    STEWARD, ROLE, REF, TXN_TIME, ATTRIB, CRED_DEF, isValidRole, \
    ATTR_NAMES, ISSUER_KEY
import datetime
import time

logger = getlogger()

MIN_TXN_TIME = time.mktime(datetime.datetime(2000, 1, 1).timetuple())


class Vertices:
    Nym = NYM
    Attribute = "Attribute"
    CredDef = "CredDef"
    IssuerKey = "IssuerKey"

    _Properties = {
        Nym: (NYM, TXN_ID, ROLE, F.seqNo.name),
        Attribute: (RAW, ENC, HASH),
        CredDef: (TYPE, ATTR_NAMES),
        IssuerKey: (REF, DATA)
    }

    @classmethod
    def properties(cls, vertexName: str):
        return cls._Properties.get(vertexName, ())


class Edges:
    AddsNym = "AddsNym"
    AddsAttribute = "AddsAttribute"
    HasAttribute = "HasAttribute"
    # TODO: Create OwnsAttribute in case user takes control of his identity
    # TODO: Create KnowsAttribute in case the attribute is shared (disclosed)
    # with someone
    AliasOf = "AliasOf"
    AddsCredDef = "AddsCredDef"
    HasIssuerKey = "HasIssuerKey"


txnEdges = {
        NYM: Edges.AddsNym,
        ATTRIB: Edges.AddsAttribute,
        CRED_DEF: Edges.AddsCredDef,
        ISSUER_KEY: Edges.HasIssuerKey
    }


txnEdgeProps = [F.seqNo.name, TXN_TIME, f.REQ_ID.nm, f.IDENTIFIER.nm,
                TARGET_NYM, NAME, VERSION]


def getEdgeByTxnType(txnType: str): return txnEdges.get(txnType)


def getTxnTypeFromEdge(edgeClass: str):
    for typ, edge in txnEdges.items():
        if edge == edgeClass:
            return typ


class IdentityGraph(OrientDbGraphStore):

    @property
    def classesNeeded(self):
        return [
            (Vertices.Nym, self.createNymClass),
            (Vertices.Attribute, self.createAttributeClass),
            (Vertices.CredDef, self.createCredDefClass),
            (Vertices.IssuerKey, self.createIssuerKeyClass),
            (Edges.AddsNym, self.createAddsNymClass),
            (Edges.AliasOf, self.createAliasOfClass),
            (Edges.AddsAttribute, self.createAddsAttributeClass),
            (Edges.HasAttribute, self.createHasAttributeClass),
            (Edges.AddsCredDef, self.createAddsCredDefClass),
            (Edges.HasIssuerKey, self.createHasIssuerClass)
        ]

    # Creates a vertex class which has a property called `nym` with a unique
    # index on it
    def createUniqueNymVertexClass(self, className, properties: Dict=None):
        d = {NYM: "string",
             VERKEY: "string"}
        if properties:
            properties.update(d)
        else:
            properties = d
        self.createVertexClass(className, properties)
        self.store.createUniqueIndexOnClass(className, NYM)

    # Creates an edge class which has a property called `txnId` with a unique
    # index on it
    def createUniqueTxnIdEdgeClass(self, className, properties: Dict=None):
        defaultProperties = {
            TXN_ID: "string",
            TXN_TIME: "datetime"
        }
        if properties:
            properties.update(defaultProperties)
        else:
            properties = defaultProperties
        self.createEdgeClass(className, properties=properties)
        self.store.createUniqueIndexOnClass(className, TXN_ID)

    def createEdgeClassWithTxnData(self, className, properties: Dict = None):
        defaultProperties = {
            TXN_ID: "string",
            TXN_TIME: "datetime",
            TXN_TYPE: "string",
            f.REQ_ID.nm: "integer",
            f.IDENTIFIER.nm: "string",
            F.seqNo.name: "string",
        }
        properties.update(defaultProperties)
        self.createUniqueTxnIdEdgeClass(className, properties)
        # self.client.command("create index CliIdReq on {} ({}, {})"
        #                     " unique".
        #                     format(className, f.REQ_ID.nm, f.IDENTIFIER.nm))

    def createNymClass(self):
        self.createUniqueNymVertexClass(Vertices.Nym,
                                        properties={ROLE: "string"})

    def createAttributeClass(self):
        self.createVertexClass(Vertices.Attribute,
                               properties={"data": "string"})

    def createCredDefClass(self):
        self.createVertexClass(Vertices.CredDef, properties={
            ATTR_NAMES: "string",
            TYPE: "string",
        })

    def createIssuerKeyClass(self):
        self.createVertexClass(Vertices.IssuerKey, properties={
            REF: "string",
            DATA: "string", # JSON
        })

    def createAddsNymClass(self):
        self.createEdgeClassWithTxnData(Edges.AddsNym,
                                        properties={ROLE: "string"})
        self.addEdgeConstraint(Edges.AddsNym, iN=Vertices.Nym, out=Vertices.Nym)

    def createAliasOfClass(self):
        self.createUniqueTxnIdEdgeClass(Edges.AliasOf,
                                        properties={REF: "string"})
        # if not then `iN` need to be a USER
        self.addEdgeConstraint(Edges.AliasOf, iN=Vertices.Nym,
                               out=Vertices.Nym)

    def createAddsAttributeClass(self):
        self.createEdgeClassWithTxnData(Edges.AddsAttribute,
                                        properties={TARGET_NYM: "string"})
        # Not specifying `out` here as both Sponsor and Agent can add attributes
        self.addEdgeConstraint(Edges.AddsAttribute, iN=Vertices.Attribute)

    def createHasAttributeClass(self):
        self.createUniqueTxnIdEdgeClass(Edges.HasAttribute)
        self.addEdgeConstraint(Edges.HasAttribute, iN=Vertices.Attribute)

    def createAddsCredDefClass(self):
        # TODO: Add compound index on the name and version
        self.createUniqueTxnIdEdgeClass(Edges.AddsCredDef, properties={
            NAME: "string",
            VERSION: "string"
        })
        self.addEdgeConstraint(Edges.AddsCredDef, iN=Vertices.CredDef)

    def createHasIssuerClass(self):
        self.createUniqueTxnIdEdgeClass(Edges.HasIssuerKey)
        self.addEdgeConstraint(Edges.HasAttribute, out=Vertices.Nym)

    def getEdgeByTxnId(self, edgeClassName, txnId):
        return self.getEntityByUniqueAttr(edgeClassName, TXN_ID, txnId)

    def getAddsNymEdge(self, nym):
        return self.getEntityByUniqueAttr(Edges.AddsNym, NYM, nym)

    def addNym(self, txnId, nym, verkey, role, frm=None, reference=None, seqNo=None):
        kwargs = {
            NYM: nym,
            VERKEY: verkey,
            TXN_ID: txnId,  # # Need to have txnId as a property for cases
            # where we dont know the sponsor of this nym or its a genesis nym
            ROLE: role,    # Need to have role as a property of the vertex it
            # makes faster to query roles by vertex.
        }

        if not frm:
            # In case of genesis transaction
            kwargs[F.seqNo.name] = seqNo

        self.createVertex(Vertices.Nym, **kwargs)
        if not frm:
            logger.debug("frm not available while adding nym")
        else:
            frmV = "(select from {} where {} = '{}')".format(Vertices.Nym,
                                                            NYM,
                                                            frm)
            toV = "(select from {} where {} = '{}')".format(Vertices.Nym,
                                                           NYM,
                                                           nym)
            # DEPR   Why are we defining this twice?
            # kwargs = {
            #     NYM: nym,
            #     VERKEY: verkey,
            #     ROLE: role,
            #     TXN_ID: txnId
            # }
            self.createEdge(Edges.AddsNym, frmV, toV, **kwargs)
            if reference:
                nymEdge = self.getEdgeByTxnId(Edges.AddsNym, txnId=reference)
                referredNymRid = nymEdge.oRecordData['in'].get()
                kwargs = {
                    REF: reference,
                    TXN_ID: txnId
                }
                self.createEdge(Edges.AliasOf, referredNymRid, toV, **kwargs)

    def addAttribute(self, frm, txnId, raw=None, enc=None,
                     hash=None, to=None):

        # Only one of `raw`, `enc`, `hash` should be provided so 2 should be
        # `None`
        if (raw, enc, hash).count(None) != 2:
            error("One and only one of raw, enc and hash should be provided")

        if raw:
            attrVertex = self.createVertex(Vertices.Attribute, raw=raw)
        elif enc:
            attrVertex = self.createVertex(Vertices.Attribute, enc=enc)
        elif hash:
            attrVertex = self.createVertex(Vertices.Attribute, hash=hash)

        frm = "(select from {} where {} = '{}')".format(Vertices.Nym, NYM,
                                                        frm)
        kwargs = {
            TARGET_NYM: to,
            TXN_ID: txnId,
        }
        self.createEdge(Edges.AddsAttribute, frm, attrVertex._rid, **kwargs)
        if to:
            to = "(select from {} where {} = '{}')".format(Vertices.Nym, NYM,
                                                           to)
            kwargs = {
                TXN_ID: txnId
            }
            self.createEdge(Edges.HasAttribute, to, attrVertex._rid, **kwargs)

    def addCredDef(self, frm, txnId, name, version, attrNames,
                   typ: Optional[str]=None):
        kwargs = {
            TYPE: typ,
            ATTR_NAMES: attrNames
        }
        vertex = self.createVertex(Vertices.CredDef, **kwargs)
        frm = "(select from {} where {} = '{}')".format(Vertices.Nym, NYM,
                                                        frm)
        kwargs = {
            TXN_ID: txnId,
            NAME: name,
            VERSION: version
        }
        self.createEdge(Edges.AddsCredDef, frm, vertex._rid, **kwargs)

    def addIssuerKey(self, frm, txnId, data, reference):
        kwargs = {
            DATA: json.dumps(data),
            REF: reference
        }
        vertex = self.createVertex(Vertices.IssuerKey, **kwargs)
        frm = "(select from {} where {} = '{}')".format(Vertices.Nym, NYM,
                                                        frm)
        kwargs = {
            TXN_ID: txnId,
        }
        self.createEdge(Edges.HasIssuerKey, frm, vertex._rid, **kwargs)

    def getRawAttrs(self, frm, *attrNames):
        cmd = 'select expand(outE("{}").inV("{}")) from {} where {}="{}"'.\
            format(Edges.HasAttribute, Vertices.Attribute, Vertices.Nym,
                   NYM, frm)
        allAttrsRecords = self.client.command(cmd)
        attrVIds = [a._rid for a in allAttrsRecords]
        seqNos = {}
        if attrVIds:
            edgeRecs = self.client.command("select expand(inE('{}')) from [{}]"
                                           .format(Edges.AddsAttribute,
                                                   ", ".join(attrVIds)))
            seqNos = {str(rec._in): int(rec.oRecordData.get(F.seqNo.name))
                      for rec in edgeRecs}
        result = {}
        for attrRec in allAttrsRecords:
            raw = json.loads(attrRec.oRecordData.get(RAW))
            key, value = raw.popitem()
            if len(attrNames) == 0 or key in attrNames:
                result[key] = [value, seqNos[attrRec._rid]]
        return result

    def getCredDef(self, frm, name, version):
        # TODO: Can this query be made similar to get attribute?
        cmd = "select outV('{}')[{}='{}'], expand(inV('{}')) from {} where " \
              "name = '{}' and version = '{}'".format(Vertices.Nym, NYM, frm,
                                                 Vertices.CredDef,
                                                 Edges.AddsCredDef, name,
                                                 version)
        credDefs = self.client.command(cmd)
        if credDefs:
            credDef = credDefs[0].oRecordData
            edgeData = self.client.command(
                "select expand(inE('{}')) from {}"
                    .format(Edges.AddsCredDef, credDefs[0]._rid))[0].oRecordData
            return {
                NAME: name,
                VERSION: version,
                TYPE: credDef.get(TYPE),
                F.seqNo.name: edgeData.get(F.seqNo.name),
                ATTR_NAMES: credDef.get(ATTR_NAMES),
                ORIGIN: frm,
            }
        return None

    def getIssuerKeys(self, frm, ref):
        cmd = "select expand(outE('{}').inV('{}')) from {} where " \
              "{} = '{}'".format(Edges.HasIssuerKey,
                                                      Vertices.IssuerKey,
                                                      Vertices.Nym, NYM,
                                                      frm)
        haystack = self.client.command(cmd)
        needle = None
        if haystack:
            for rec in haystack:
                if rec.oRecordData.get(REF) == str(ref):
                    needle = rec
                    break
            edgeData = self.client.command(
                "select expand(inE('{}')) from {}"
                    .format(Edges.HasIssuerKey, needle._rid))[0].oRecordData
            return {
                ORIGIN: frm,
                REF: ref,
                F.seqNo.name: edgeData.get(F.seqNo.name),
                DATA: json.loads(needle.oRecordData.get(DATA))
            }
        return None

    def getNym(self, nym, role=None):
        """
        Get a nym, if role is provided then get nym with that role
        :param nym:
        :param role:
        :return:
        """
        if not role:
            return self.getEntityByUniqueAttr(Vertices.Nym, NYM, nym)
        else:
            return self.getEntityByAttrs(Vertices.Nym, {
                NYM: nym,
                ROLE: role
            })

    def getSteward(self, nym):
        return self.getNym(nym, STEWARD)

    def getSponsor(self, nym):
        return self.getNym(nym, SPONSOR)

    def getUser(self, nym):
        return self.getNym(nym, USER)

    def hasSteward(self, nym):
        return bool(self.getSteward(nym))

    def hasSponsor(self, nym):
        return bool(self.getSponsor(nym))

    def hasUser(self, nym):
        return bool(self.getUser(nym))

    def hasNym(self, nym):
        return bool(self.getNym(nym))

    def getRole(self, nym):
        nymV = self.getNym(nym)
        if not nymV:
            raise ValueError("Nym does not exist")
        else:
            return nymV.oRecordData.get(ROLE)

    def getSponsorFor(self, nym):
        sponsor = self.client.command("select expand (out) from {} where "
                                   "{} = '{}'".format(Edges.AddsNym,
                                                      NYM, nym))
        return None if not sponsor else sponsor[0].oRecordData.get(NYM)

    def countStewards(self):
        return self.countEntitiesByAttrs(Vertices.Nym, {ROLE: STEWARD})

    def getAddNymTxn(self, nym):
        nymEdge = self.getAddsNymEdge(nym)
        if not nymEdge:
            # For the special case where steward(s) are added through genesis
            # transactions so they wont have an edge
            nymV = self.getNym(nym)
            if not nymV:
                return None
            else:
                return {
                    TXN_ID: nymV.oRecordData.get(TXN_ID),
                    TARGET_NYM: nym,
                    ROLE: nymV.oRecordData.get(ROLE)
                }
        else:
            result = {
                TXN_ID: nymEdge.oRecordData.get(TXN_ID),
                ROLE: nymEdge.oRecordData.get(ROLE) or USER
            }
            frm, to = self.store.getByRecordIds(nymEdge.oRecordData['out'].get(),
                                          nymEdge.oRecordData['in'].get())
            result[f.IDENTIFIER.nm] = frm.oRecordData.get(NYM)
            result[TARGET_NYM] = to.oRecordData.get(NYM)
            return result

    def getAddAttributeTxnIds(self, nym):
        attrEdges = self.client.command("select {} from {} where {} = '{}'".
                                        format(TXN_ID, Edges.AddsAttribute,
                                               TARGET_NYM, nym)) or []
        return [edge.oRecordData[TXN_ID] for edge in attrEdges]

    def getTxn(self, identifier, reqId, **kwargs):
        typ = kwargs[TXN_TYPE]
        edgeClass = getEdgeByTxnType(typ)
        edgeProps = ", ".join("@this.{} as __e_{}".format(name, name) for name in
                              txnEdgeProps)
        vertexProps = ", ".join("in.{} as __v_{}".format(name, name) for name in
                                chain.from_iterable(
                                    Vertices._Properties.values()))
        cmd = "select {}, {} from {} where {} = '{}' and {} = {}". \
            format(edgeProps, vertexProps, edgeClass, f.IDENTIFIER.nm,
                   identifier, f.REQ_ID.nm, reqId)

        result = self.client.command(cmd)
        return None if not result \
            else self.makeResult(typ, self.cleanKeyNames(result[0].oRecordData))

    def getResultForTxnIds(self, *txnIds, seqNo=None) -> dict:
        txnIds = set(txnIds)
        txnIdsStr = ",".join(["'{}'".format(tid) for tid in txnIds])

        def getTxnsFromEdge(edgeClass):
            # TODO: Need to do this to get around a bug in pyorient,
            # https://github.com/mogui/pyorient/issues/207
            edgeProps = ", ".join("@this.{} as __e_{}".format(name, name)
                                  for name in txnEdgeProps)
            vertexProps = ", ".join("in.{} as __v_{}".format(name, name)
                                    for name in chain.from_iterable(
                                        Vertices._Properties.values()))
            cmd = "select {}, {} from {} where {} in [{}]".\
                format(edgeProps, vertexProps, edgeClass, TXN_ID, txnIdsStr)
            if seqNo:
                cmd += " and {} > {}".format(F.seqNo.name, seqNo)
            result = self.client.command(cmd)
            if not result:
                return {}
            else:
                out = {}
                for r in result:
                    if r.oRecordData:
                        oRecordData = self.cleanKeyNames(r.oRecordData)
                        out[oRecordData[F.seqNo.name]] = self.makeResult(
                            NYM, oRecordData)
                return out

        result = reduce(lambda d1, d2: {**d1, **d2},
                      map(getTxnsFromEdge, list(txnEdges.values())))

        if len(txnIds) > len(result):
            # Some transactions missing so look for transactions without edges
            result.update(self.getTxnsWithoutEdge(*(txnIds.difference(
                {r.get(TXN_ID) for r in result.values()})), seqNo=seqNo))
        return result

    def getTxnsWithoutEdge(self, *txnIds, seqNo=None):
        # For getting transactions for which have no edges in the graph as in
        # case of genesis transactions, currently looking for only `NYM`
        # transactions
        txnIdsStr = ",".join(["'{}'".format(tid) for tid in txnIds])
        cmd = "select from {} where {} in [{}]".format(Vertices.Nym, TXN_ID,
                                                       txnIdsStr)
        if seqNo:
            cmd += " and {} > {}".format(F.seqNo.name, seqNo)
        result = self.client.command(cmd)
        if not result:
            return {}
        else:
            out = {}
            for r in result:
                if r.oRecordData:
                    r.oRecordData[TARGET_NYM] = r.oRecordData.pop(NYM)
                    out[r.oRecordData[F.seqNo.name]] = self.makeResult(
                        NYM, r.oRecordData)
            return out

    def _updateTxnIdEdgeWithTxn(self, txnId, edgeClass, txn, properties=None):
        properties = properties or txnEdgeProps
        updates = ', '.join(["{}={}".format(prop, txn[prop])
                             if isinstance(txn[prop], (int, float)) else
                             "{}='{}'".format(prop, txn[prop])
                             for prop in properties if (prop in txn and
                                                        txn[prop] is not None)])
        updateCmd = "update {} set {} where {}='{}'". \
            format(edgeClass, updates, TXN_ID, txnId)
        logger.debug("updating edge {} with command {}".format(edgeClass,
                                                               updateCmd))
        self.client.command(updateCmd)

    def addNymTxnToGraph(self, txn):
        origin = txn.get(f.IDENTIFIER.nm)
        role = txn.get(ROLE) or USER
        if not isValidRole(role):
            raise ValueError("Unknown role {} for nym, cannot add nym to graph"
                             .format(role))
        nym = txn[TARGET_NYM]
        # Not using `txn.get(VERKEY, '') as txn might have VERKEY but set as None`
        verkey = txn.get(VERKEY) or ''
        try:
            txnId = txn[TXN_ID]
            self.addNym(txnId, nym, verkey, role,
                        frm=origin, reference=txn.get(REF),
                        seqNo=txn.get(F.seqNo.name))
            self._updateTxnIdEdgeWithTxn(txnId, Edges.AddsNym, txn)
        except pyorient.PyOrientORecordDuplicatedException:
            logger.debug("The nym {} was already added to graph".
                         format(nym))
        except pyorient.PyOrientCommandException as ex:
            fault(ex, "An exception was raised while adding "
                      "nym {}: {}".format(nym, ex))

    def addAttribTxnToGraph(self, txn):
        origin = txn.get(f.IDENTIFIER.nm)
        txnId = txn[TXN_ID]
        try:
            self.addAttribute(frm=origin, txnId=txnId, raw=txn.get(RAW),
                              enc=txn.get(ENC), hash=txn.get(HASH),
                              to=txn.get(TARGET_NYM))
            self._updateTxnIdEdgeWithTxn(txnId, Edges.AddsAttribute, txn)
        except pyorient.PyOrientCommandException as ex:
            fault(ex, "An exception was raised while adding attribute: {}".
                  format(ex))

    def addCredDefTxnToGraph(self, txn):
        origin = txn.get(f.IDENTIFIER.nm)
        txnId = txn[TXN_ID]
        data = txn.get(DATA)
        try:
            self.addCredDef(
                frm=origin,
                txnId=txnId,
                name=data.get(NAME),
                version=data.get(VERSION),
                attrNames=data.get(ATTR_NAMES),
                typ=data.get(TYPE))
            self._updateTxnIdEdgeWithTxn(txnId, Edges.AddsCredDef, txn)
        except Exception as ex:
            fault(ex, "Error adding cred def to orientdb")

    def addIssuerKeyTxnToGraph(self, txn):
        origin = txn.get(f.IDENTIFIER.nm)
        txnId = txn[TXN_ID]
        data = txn.get(DATA)
        try:
            self.addIssuerKey(
                frm=origin,
                txnId=txnId,
                data=data,
                reference=txn.get(REF),
                )
            self._updateTxnIdEdgeWithTxn(txnId, Edges.HasIssuerKey, txn)
        except Exception as ex:
            fault(ex, "Error adding issuer key to orientdb")
        pass

    def countTxns(self):
        seqNos = set()
        for txnEdgeClass in (list(txnEdges.values())+[Vertices.Nym]):
            cmd = "select distinct({}) as seqNo from {}". \
                format(F.seqNo.name, txnEdgeClass)
            result = self.client.command(cmd)
            seqNos.update({r.oRecordData.get('seqNo') for r in result})
        return len(seqNos)

    @staticmethod
    def cleanKeyNames(oRecordData):
        # Removing `__e_` and `__v_` from key names of oRecordData.
        # They are added to make select queries work which can contain
        # duplicate key names
        return {k[4:] if (k.startswith("__e_") or k.startswith("__v_")) else k:
                    v for k, v in oRecordData.items()}

    @staticmethod
    def makeResult(txnType, oRecordData):
        try:
            int(oRecordData.get(F.seqNo.name))
        except TypeError as ex:
            logger.debug(
                "Cannot convert {} to integer. Provided oRecordData {} for type"
                " {}".format(oRecordData.get(F.seqNo.name), oRecordData,
                             txnType))
            return {}

        result = {
            F.seqNo.name: int(oRecordData.get(F.seqNo.name)),
            TXN_TYPE: txnType,
            TXN_ID: oRecordData.get(TXN_ID),
            f.REQ_ID.nm: oRecordData.get(f.REQ_ID.nm),
            f.IDENTIFIER.nm: oRecordData.get(f.IDENTIFIER.nm),
        }

        if TXN_TIME in oRecordData:
            txnTime = oRecordData.get(TXN_TIME)
            if isinstance(txnTime, datetime.datetime):
                try:
                    txnTimeStamp = int(time.mktime(txnTime.timetuple()))
                except (OverflowError, ValueError) as ex:
                    logger.warn("TXN_TIME cannot convert datetime '{}' "
                                "to timestamp, reject it".format(txnTime))
                else:
                    # TODO The right thing to do is check the time of the PRE-PREPARE.
                    # https://github.com/evernym/sovrin-priv/pull/20#discussion_r80387554
                    if MIN_TXN_TIME < txnTimeStamp < time.time():
                        result[TXN_TIME] = txnTimeStamp
                    else:
                        logger.warn("TXN_TIME {} is not in the range ({}, {}), "
                                    "reject it".format(txnTimeStamp, MIN_TXN_TIME, time.time()))

        if TARGET_NYM in oRecordData:
            result[TARGET_NYM] = oRecordData[TARGET_NYM]

        if txnType == NYM:
            result[ROLE] = oRecordData.get(ROLE)

        if txnType == ATTRIB:
            for n in [RAW, ENC, HASH]:
                if n in oRecordData:
                    result[n] = oRecordData[n]
                    break

        if txnType == CRED_DEF:
            result[DATA] = {}
            for n in [IP, PORT, KEYS, TYPE, NAME, VERSION]:
                if n in oRecordData:
                    result[DATA][n] = oRecordData[n]

        return result
