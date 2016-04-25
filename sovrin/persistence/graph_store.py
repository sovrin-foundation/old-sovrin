from collections import OrderedDict
from typing import Dict

import pyorient
from plenum.common.util import getlogger

from sovrin.common.txn import NYM, TXN_ID, TARGET_NYM, USER, SPONSOR, STEWARD, \
    ROLE, ORIGIN, REFERENCE, TXN_TIME
from plenum.persistence.graph_store import GraphStore as PlenumGraphStore

logger = getlogger()


class Vertices:
    Nym = NYM
    Steward = STEWARD
    Sponsor = SPONSOR
    User = USER
    Attribute = "Attribute"


class Edges:
    AddedNym = "AddedNym"
    AddedAttribute = "AddedAttribute"
    HasAttribute = "HasAttribute"
    # TODO Later have OwnsAttribute in case user takes control of his identity
    Sponsors = "Sponsors"
    AliasOf = "AliasOf"


class GraphStore(PlenumGraphStore):

    def classesNeeded(self):
        return [
            (Vertices.Nym, self.createNymClass),
            (Vertices.Steward, self.createStewardClass),
            (Vertices.Sponsor, self.createSponsorClass),
            (Vertices.User, self.createUserClass),
            (Vertices.Attribute, self.createAttributeClass),
            (Edges.AddedNym, self.createAddedNymClass),
            (Edges.AliasOf, self.createAliasOfClass),
            (Edges.Sponsors, self.createSponsorsClass),
            (Edges.AddedAttribute, self.createAddedAttributeClass),
            (Edges.HasAttribute, self.createHasAttributeClass),
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

    def createNymClass(self):
        self.createUniqueNymVertexClass(Vertices.Nym)

    def createStewardClass(self):
        self.client.command("create class {} extends {}".
                            format(Vertices.Steward, Vertices.Nym))

    def createSponsorClass(self):
        self.client.command("create class {} extends {}".
                            format(Vertices.Sponsor, Vertices.Nym))

    def createUserClass(self):
        self.client.command("create class {} extends {}".
                            format(Vertices.User, Vertices.Nym))

    def createAttributeClass(self):
        self.createVertexClass(Vertices.Attribute,
                               properties={"data": "string"})

    def createAddedNymClass(self):
        # TODO: Confirm that property ROLE is not needed
        self.createUniqueTxnIdEdgeClass(Edges.AddedNym,
                                        properties={ROLE: "string"})
        self.addEdgeConstraint(Edges.AddedNym, iN=Vertices.Nym, out=Vertices.Nym)

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

    def createAddedAttributeClass(self):
        self.createUniqueTxnIdEdgeClass(Edges.AddedAttribute,
                                        properties={TARGET_NYM: "string"})
        # Not specifying `out` here as both Sponsor and Agent can add attributes
        self.addEdgeConstraint(Edges.AddedAttribute, iN=Vertices.Attribute)

    def createHasAttributeClass(self):
        self.createUniqueTxnIdEdgeClass(Edges.HasAttribute)
        self.addEdgeConstraint(Edges.HasAttribute, iN=Vertices.Attribute)

    def getEdgeByTxnId(self, edgeClassName, txnId):
        result = self.client.command("select from {} where {} = '{}'".
                                     format(edgeClassName, TXN_ID, txnId))
        return None if not result else result[0]

    def getAddedNymEdge(self, nym):
        nymEdge = self.client.command("select from {} where {} = '{}'".
                                      format(Edges.AddedNym, NYM, nym))
        if not nymEdge:
            return None
        else:
            return nymEdge[0]

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
            self.createEdge(Edges.AddedNym, frm, to, **kwargs)

    def addSponsor(self, txnId, nym, frm=None):
        # Add the sponsor
        if not frm:
            logger.debug("frm not available while adding sponsor")
            self.createVertex(Vertices.Sponsor, nym=nym)
        else:
            self.createVertex(Vertices.Sponsor, nym=nym, frm=frm)

            # Now add an edge from steward to sponsor, since only
            # a steward can create a sponsor
            frm = "(select from {} where {} = '{}')".format(Vertices.Steward, NYM, frm)
            to = "(select from {} where {} = '{}')".format(Vertices.Sponsor, NYM, nym)
            # Let there be an error in edge creation if `frm` does not exist
            # because if system is behaving correctly then `frm` would exist
            kwargs = {
                NYM: nym,
                ROLE: SPONSOR,
                TXN_ID: txnId
            }
            self.createEdge(Edges.AddedNym, frm, to, **kwargs)

    # TODO: Consider if sponsors or stewards would have aliases too
    def addUser(self, txnId, nym, frm=None, reference=None):
        # Add the user
        if not frm:
            logger.debug("frm not available while adding user")
            self.createVertex(Vertices.User, nym=nym)
        else:
            self.createVertex(Vertices.User, nym=nym, frm=frm)

            # # TODO: After implementing agents, check if `frm` is agent
            typ = self.getRole(frm)
            # Now add an edge from SPONSOR to USER
            frm = "(select from {} where {} = '{}')".format(typ, NYM, frm)
            to = "(select from {} where {} = '{}')".format(Vertices.User, NYM, nym)
            # Let there be an error in edge creation if `frm` does not exist
            # because if system is behaving correctly then `frm` would exist
            kwargs = {
                NYM: nym,
                ROLE: USER,
                TXN_ID: txnId
            }
            self.createEdge(Edges.AddedNym, frm, to, **kwargs)
            if typ == Vertices.Sponsor:
                kwargs = {
                    TXN_ID: txnId
                }
                self.createEdge(Edges.Sponsors, frm, to, **kwargs)
            if reference:
                kwargs = {
                    TXN_ID: reference
                }
                nymEdge = self.getEdgeByTxnId(Edges.AddedNym, **kwargs)
                referredNymRid = nymEdge.oRecordData['in'].get()
                kwargs = {
                    REFERENCE: reference,
                    TXN_ID: txnId
                }
                self.createEdge(Edges.AliasOf, referredNymRid, to, **kwargs)

    def addAttribute(self, frm, to, data, txnId):
        attrVertex = self.createVertex(Vertices.Attribute, data=data)

        frm = "(select from {} where {} = '{}')".format(Vertices.Nym, NYM,
                                                        frm)
        kwargs = {
            TARGET_NYM: to,
            TXN_ID: txnId
        }
        self.createEdge(Edges.AddedAttribute, frm, attrVertex._rid, **kwargs)

        # to = "(select from {} where {} = '{}')".format(Vertices.User, NYM, to)
        to = "(select from {} where {} = '{}')".format(Vertices.Nym, NYM,
                                                       to)
        kwargs = {
            TXN_ID: txnId
        }
        self.createEdge(Edges.HasAttribute, to, attrVertex._rid, **kwargs)

    def getNym(self, nym):
        result = self.client.command("select from {} where {} = '{}'".
                            format(Vertices.Nym, NYM, nym))
        if not result:
            return None
        else:
            return result[0]

    def getUser(self, nym):
        result = self.client.command("select from {} where {} = '{}'".
                                     format(Vertices.User, NYM, nym))
        if not result:
            return None
        else:
            return result[0]

    def hasSteward(self, nym):
        return bool(self.client.command("select from {} where {} = '{}'".
                                        format(Vertices.Steward, NYM, nym)))

    def hasSponsor(self, nym):
        return bool(self.client.command("select from {} where {} = '{}'".
                                        format(Vertices.Sponsor, NYM, nym)))

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
        if not sponsor:
            return None
        else:
            return sponsor[0].oRecordData.get(NYM)

    def getAddNymTxn(self, nym):
        nymEdge = self.getAddedNymEdge(nym)
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
                TXN_ID: nymEdge.oRecordData.get(TXN_ID)
            }
            frm, to = self.store.getByRecordIds(nymEdge.oRecordData['out'].get(),
                                          nymEdge.oRecordData['in'].get())
            result[ORIGIN] = frm.oRecordData.get(NYM)
            result[TARGET_NYM] = to.oRecordData.get(NYM)
            return result

    def getAddAttributeTxnIds(self, nym):
        attrEdges = self.client.command("select {} from {} where {} = '{}'".
                                      format(TXN_ID, Edges.AddedAttribute,
                                             TARGET_NYM, nym))
        if not attrEdges:
            return []
        else:
            return [edge.oRecordData[TXN_ID] for edge in attrEdges]
