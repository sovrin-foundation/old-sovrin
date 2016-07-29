import json
from functools import reduce
from typing import Dict, Optional

from ledger.util import F
from plenum.common.txn import TXN_TYPE, TYPE, IP, PORT, KEYS, NAME, VERSION, \
    DATA
from plenum.common.types import f, Reply
from plenum.common.util import getlogger, error
from plenum.persistence.orientdb_graph_store import OrientDbGraphStore
from sovrin.common.txn import NYM, TXN_ID, TARGET_NYM, USER, SPONSOR, \
    STEWARD, ROLE, ORIGIN, REFERENCE, TXN_TIME, ATTRIB, CRED_DEF

logger = getlogger()


class Vertices:
    Nym = NYM
    Steward = STEWARD
    Sponsor = SPONSOR
    User = USER
    Attribute = "Attribute"
    CredDef = "CredDef"


class Edges:
    AddsNym = "AddsNym"
    AddsAttribute = "AddsAttribute"
    HasAttribute = "HasAttribute"
    # TODO Later have OwnsAttribute in case user takes control of his identity
    Sponsors = "Sponsors"
    AliasOf = "AliasOf"
    AddsCredDef = "AddsCredDef"

txnEdges = {
        NYM: Edges.AddsNym,
        ATTRIB: Edges.AddsAttribute,
        CRED_DEF: Edges.AddsCredDef
    }


def getEdgeFromType(txnType: str): return txnEdges.get(txnType)


class IdentityGraph(OrientDbGraphStore):

    def classesNeeded(self):
        return [
            (Vertices.Nym, self.createNymClass),
            (Vertices.Steward, self.createStewardClass),
            (Vertices.Sponsor, self.createSponsorClass),
            (Vertices.User, self.createUserClass),
            (Vertices.Attribute, self.createAttributeClass),
            (Vertices.CredDef, self.createCredDefClass),
            (Edges.AddsNym, self.createAddsNymClass),
            (Edges.AliasOf, self.createAliasOfClass),
            (Edges.Sponsors, self.createSponsorsClass),
            (Edges.AddsAttribute, self.createAddsAttributeClass),
            (Edges.HasAttribute, self.createHasAttributeClass),
            (Edges.AddsCredDef, self.createAddsCredDefClass)
        ]

    # Creates a vertex class which has a property called `nym` with a unique
    # index on it
    def createUniqueNymVertexClass(self, className, properties: Dict=None):
        if properties:
            properties.update({NYM: "string"})
        else:
            properties = {NYM: "string"}
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
        self.createUniqueNymVertexClass(Vertices.Nym)

    def createStewardClass(self):
        self.createClass(Vertices.Steward, Vertices.Nym)

    def createSponsorClass(self):
        self.createClass(Vertices.Sponsor, Vertices.Nym)

    def createUserClass(self):
        self.createClass(Vertices.User, Vertices.Nym)

    def createAttributeClass(self):
        self.createVertexClass(Vertices.Attribute,
                               properties={"data": "string"})

    def createCredDefClass(self):
        self.createVertexClass(Vertices.CredDef, properties={
            TYPE: "string",
            IP: "string",
            PORT: "integer",
            KEYS: "string"      # JSON
        })

    def createAddsNymClass(self):
        # TODO: Confirm that property ROLE is not needed
        self.createEdgeClassWithTxnData(Edges.AddsNym,
                                        properties={ROLE: "string"})
        self.addEdgeConstraint(Edges.AddsNym, iN=Vertices.Nym, out=Vertices.Nym)

    def createAliasOfClass(self):
        self.createUniqueTxnIdEdgeClass(Edges.AliasOf,
                                        properties={REFERENCE: "string"})
        # TODO: Consider if sponsors or stewards would have aliases too,
        # if not then `iN` need to be a USER
        self.addEdgeConstraint(Edges.AliasOf, iN=Vertices.Nym,
                               out=Vertices.Nym)

    def createSponsorsClass(self):
        self.createUniqueTxnIdEdgeClass(Edges.Sponsors)
        self.addEdgeConstraint(Edges.Sponsors, iN=Vertices.User,
                               out=Vertices.Sponsor)

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

    def getEdgeByTxnId(self, edgeClassName, txnId):
        return self.getEntityByUniqueAttr(edgeClassName, TXN_ID, txnId)

    def getAddsNymEdge(self, nym):
        return self.getEntityByUniqueAttr(Edges.AddsNym, NYM, nym)

    def addSteward(self, txnId, nym, frm=None):
        # Add the steward
        if not frm:
            logger.debug("frm not available while adding steward")
            kwargs = {
                NYM: nym,
                TXN_ID: txnId
            }
            self.createVertex(Vertices.Steward, **kwargs)
        else:
            self.createVertex(Vertices.Steward, nym=nym, frm=frm)

            # Now add an edge from from another steward to this steward, since only
            # a steward can create a steward
            frm = "(select from {} where {} = '{}')".format(Vertices.Steward, NYM,
                                                             frm)
            to = "(select from {} where {} = '{}')".format(Vertices.Steward, NYM,
                                                            nym)
            # Let there be an error in edge creation if `frm` does not exist
            # because if system is behaving correctly then `frm` would exist
            kwargs = {
                NYM: nym,
                ROLE: STEWARD,
                TXN_ID: txnId
            }
            self.createEdge(Edges.AddsNym, frm, to, **kwargs)

    def addSponsor(self, txnId, nym, frm=None):
        # Add the sponsor
        if not frm:
            logger.debug("frm not available while adding sponsor")
            self.createVertex(Vertices.Sponsor, nym=nym)
        else:
            self.createVertex(Vertices.Sponsor, nym=nym, frm=frm)

            # Now add an edge from steward to sponsor, since only
            # a steward can create a sponsor
            frm = "(select from {} where {} = '{}')".format(
                Vertices.Steward, NYM, frm)
            to = "(select from {} where {} = '{}')".format(
                Vertices.Sponsor, NYM, nym)
            # Let there be an error in edge creation if `frm` does not
            # exist because if system is behaving correctly then `frm`
            #  would exist
            kwargs = {
                NYM: nym,
                ROLE: SPONSOR,
                TXN_ID: txnId
            }
            self.createEdge(Edges.AddsNym, frm, to, **kwargs)

    # TODO: Consider if sponsors or stewards would have aliases too
    def addUser(self, txnId, nym, frm=None, reference=None):
        # Add the user
        if not frm:
            logger.debug("frm not available while adding user")
            self.createVertex(Vertices.User, nym=nym)
        else:
            self.createVertex(Vertices.User, nym=nym, frm=frm)

            # TODO: After implementing agents, check if `frm` is agent
            typ = self.getRole(frm)
            # Now add an edge from SPONSOR to USER
            frm = "(select from {} where {} = '{}')".format(typ, NYM, frm)
            to = "(select from {} where {} = '{}')".format(Vertices.User, NYM,
                                                           nym)
            # Let there be an error in edge creation if `frm` does not
            #  exist because if system is behaving correctly then `frm`
            #  would exist
            kwargs = {
                NYM: nym,
                ROLE: USER,
                TXN_ID: txnId
            }
            self.createEdge(Edges.AddsNym, frm, to, **kwargs)
            if typ == Vertices.Sponsor:
                kwargs = {
                    TXN_ID: txnId
                }
                self.createEdge(Edges.Sponsors, frm, to, **kwargs)
            if reference:
                kwargs = {
                    TXN_ID: reference
                }
                nymEdge = self.getEdgeByTxnId(Edges.AddsNym, **kwargs)
                referredNymRid = nymEdge.oRecordData['in'].get()
                kwargs = {
                    REFERENCE: reference,
                    TXN_ID: txnId
                }
                self.createEdge(Edges.AliasOf, referredNymRid, to, **kwargs)

    def addAttribute(self, frm, txnId, txnTime=None, raw=None, enc=None,
                     hash=None, to=None):
        if raw:
            attrVertex = self.createVertex(Vertices.Attribute, raw=raw)
        elif enc:
            attrVertex = self.createVertex(Vertices.Attribute, enc=enc)
        elif hash:
            attrVertex = self.createVertex(Vertices.Attribute, hash=hash)
        else:
            error("Only one of raw, enc and hash should be provided")

        frm = "(select from {} where {} = '{}')".format(Vertices.Nym, NYM,
                                                        frm)
        kwargs = {
            TARGET_NYM: to,
            TXN_ID: txnId,
        }
        if txnTime is not None:
            kwargs[TXN_TIME] = int(txnTime)
        self.createEdge(Edges.AddsAttribute, frm, attrVertex._rid, **kwargs)
        # to = "(select from {} where {} = '{}')".format(Vertices.User, NYM, to)
        to = "(select from {} where {} = '{}')".format(Vertices.Nym, NYM,
                                                       to)
        kwargs = {
            TXN_ID: txnId
        }
        self.createEdge(Edges.HasAttribute, to, attrVertex._rid, **kwargs)

    def addCredDef(self, frm, txnId, txnTime, name, version, keys: Dict,
                   typ: Optional[str]=None, ip: Optional[str]=None,
                   port: Optional[int]=None):
        kwargs = {
            TYPE: typ,
            IP: ip,
            PORT: port,
            KEYS: json.dumps(keys),
            # TODO: Remove these 2 attributes since they are there in edge
            NAME: name,
            VERSION: version
        }
        vertex = self.createVertex(Vertices.CredDef, **kwargs)
        frm = "(select from {} where {} = '{}')".format(Vertices.Nym, NYM,
                                                        frm)
        kwargs = {
            TXN_ID: txnId,
            NAME: name,
            VERSION: version
        }
        if txnTime is not None:
            kwargs[TXN_TIME] = int(txnTime)
        self.createEdge(Edges.AddsCredDef, frm, vertex._rid, **kwargs)

    def getCredDef(self, frm, name, version):
        credDefs = self.client.command("select expand(out('{}')) from "
                                       "{} where {}='{}'"
                                       .format(Edges.AddsCredDef, Vertices.Nym,
                                               NYM, frm))
        if credDefs:
            for cd in credDefs:
                record = cd.oRecordData
                if record.get(NAME) == name and record.get(VERSION) == version:
                    return {
                        NAME: name,
                        VERSION: version,
                        IP: record.get(IP),
                        PORT: record.get(PORT),
                        TYPE: record.get(TYPE),
                        KEYS: record.get(KEYS)
                    }

    def getNym(self, nym):
        # cmd = "select from {} where {} = '{}'".format(Vertices.Nym, NYM, nym)
        # try:
        #     result = self.client.command(cmd)
        # except Exception as ex:
        #     print("error executing command {} {}".format(cmd, ex))
        #     raise ex
        # return result and result[0]
        return self.getEntityByUniqueAttr(Vertices.Nym, NYM, nym)

    def getSteward(self, nym):
        return self.getEntityByUniqueAttr(Vertices.Steward, NYM, nym)

    def getSponsor(self, nym):
        return self.getEntityByUniqueAttr(Vertices.Sponsor, NYM, nym)

    def getUser(self, nym):
        return self.getEntityByUniqueAttr(Vertices.User, NYM, nym)

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
            return nymV._class

    def getSponsorFor(self, nym):
        sponsor = self.client.command("select expand (in('{}')) from {} where "
                                   "{} = '{}'".format(Edges.Sponsors,
                                                      Vertices.User, NYM, nym))
        return None if not sponsor else sponsor[0].oRecordData.get(NYM)

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
                    TARGET_NYM: nym
                }
        else:
            result = {
                TXN_ID: nymEdge.oRecordData.get(TXN_ID),
                ROLE: nymEdge.oRecordData.get(ROLE, USER)
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
        type = kwargs[TXN_TYPE]
        edgeClass = getEdgeFromType(type)
        result = self.client.command("select from {} where "
                                     "clientId = '{}' and reqId = {}".
                                     format(edgeClass, identifier, reqId))
        return None if not result \
            else result[0].oRecordData.get('reply')

    def getRepliesForTxnIds(self, *txnIds, seqNo=None) -> dict:
        txnIds = ",".join(["'{}'".format(tid) for tid in txnIds])

        def delegate(edgeClass):
            cmd = "select EXPAND(@this.exclude('in', 'out')) from {} where {}" \
                  " in [{}]". \
                format(edgeClass, TXN_ID, txnIds)
            if seqNo:
                cmd += " and seqNo > {}".format(seqNo)
            result = self.client.command(cmd)
            return {} if not result else \
                {r.oRecordData["seqNo"]: r.oRecordData for r in result}

        return reduce(lambda d1, d2: {**d1, **d2},
                      map(delegate, list(txnEdges.values())))

    def storeReply(self, reply: Reply):
        # TODO: This stores all data in the edge, fix it ASAP.
        edgeClass = getEdgeFromType(reply.result[TXN_TYPE])
        assert reply.result[TXN_ID]
        updateCmd = self._updateProperties(reply.result, edgeClass,
                                           reply.result[TXN_ID])
        self.client.command(updateCmd)

    @staticmethod
    def _updateProperties(props, edgeClass, txnId):
        intTypes = [F.seqNo.name, TXN_TIME, f.REQ_ID.nm]
        auditPath = props.get(F.auditPath.name)
        if auditPath:
            props[F.auditPath.name] = ",".join(auditPath)

        # TODO: Temporary fix, fix it ASAP.
        if DATA in props and not isinstance(props[DATA], str):
            props[DATA] = json.dumps(props[DATA])
        updates = ', '.join(["{}='{}'".format(x, props[x])
                             if x not in intTypes else
                             "{}={}".format(x, props[x])
                             for x in props if props[x]])
        updateCmd = "update {} set {} upsert where {}='{}'". \
            format(edgeClass, updates, TXN_ID, txnId)
        return updateCmd
