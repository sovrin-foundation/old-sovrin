from collections import OrderedDict
from typing import Dict

import pyorient

from plenum.common.util import getlogger
from sovrin.common.txn import NYM, TXN_ID, TARGET_NYM, USER, SPONSOR, STEWARD, \
    ROLE, ORIGIN, REFERENCE

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


class GraphStorage:
    def __init__(self, user, password, dbName, host="localhost", port=2424,
                 storageType=pyorient.STORAGE_TYPE_MEMORY):
        self.client = pyorient.OrientDB(host=host, port=port)
        self.session_id = self.client.connect(user, password)
        if not self.client.db_exists(dbName, storageType):
            logger.debug("Creating GraphDB {}".format(dbName))
            self.client.db_create(dbName, pyorient.DB_TYPE_GRAPH, storageType)
        self.client.db_open(dbName, user, password)
        self.bootstrap()

    def classExists(self, name: str) -> bool:
        r = self.client.command("select from ( select expand( classes ) from "
                                 "metadata:schema ) where name = '{}'".
                                 format(name))
        return bool(r)

    def createClassProperties(self, className, properties: Dict):
        for prpName, typ in properties.items():
            self.client.command("create property {}.{} {}".format(className,
                                                                  prpName, typ))

    def createIndexOnClass(self, className: str, prop, indexType=None):
        cmd = "create index {}.{}".format(className, prop)
        if indexType:
            if indexType not in ("unique", ):
                raise ValueError("Unknown index type {}".format(indexType))
            cmd += " {}".format(indexType)
        self.client.command(cmd)

    def createUniqueIndexOnClass(self, className, uniqueProperty):
        self.createIndexOnClass(className, uniqueProperty, "unique")

    def createVertexClass(self, className: str, properties: Dict=None):
        self.client.command("create class {} extends V".format(className))
        if properties:
            self.createClassProperties(className, properties)

    def createEdgeClass(self, className: str, properties: Dict=None):
        self.client.command("create class {} extends E".format(className))
        if properties:
            self.createClassProperties(className, properties)

    def addEdgeConstraint(self, edgeClass, iN=None, out=None):
        if iN:
            self.client.command("create property {}.in link {}".
                                format(edgeClass, iN))
        if out:
            self.client.command("create property {}.out link {}".
                                format(edgeClass, out))

    # Creates a vertex class which has a property called `nym` with a unique
    # index on it
    def createUniqueNymVertexClass(self, className, properties: Dict=None):
        if properties:
            properties.update({NYM: "string"})
        else:
            properties = {NYM: "string"}
        self.createVertexClass(className, properties)
        self.createUniqueIndexOnClass(className, NYM)

    # Creates an edge class which has a property called `txnId` with a unique
    # index on it
    def createUniqueTxnIdEdgeClass(self, className, properties: Dict=None):
        if properties:
            properties.update({TXN_ID: "string"})
        else:
            properties = {TXN_ID: "string"}
        self.createEdgeClass(className, properties=properties)
        self.createUniqueIndexOnClass(className, TXN_ID)

    def createNymClass(self):
        self.createUniqueNymVertexClass(Vertices.Nym)

    def createStewardClass(self):
        # self.createUniqueNymVertexClass(Vertices.Steward)
        self.client.command("create class {} extends {}".
                            format(Vertices.Steward, Vertices.Nym))

    def createSponsorClass(self):
        # self.createUniqueNymVertexClass(Vertices.Sponsor)
        self.client.command("create class {} extends {}".
                            format(Vertices.Sponsor, Vertices.Nym))

    def createUserClass(self):
        # self.createUniqueNymVertexClass(Vertices.User)
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

    def createEntity(self, createCmd, **kwargs):
        attributes = []
        if len(kwargs) > 0:
            createCmd += " set "
        for key, val in kwargs.items():
            attributes.append("{} = '{}'".format(key, val))
        createCmd += ", ".join(attributes)
        return self.client.command(createCmd)[0]

    def createVertex(self, name, **kwargs):
        cmd = "create vertex {}".format(name)
        return self.createEntity(cmd, **kwargs)

    def createEdge(self, name, frm, to, **kwargs):
        cmd = "create edge {} from {} to {}".format(name, frm, to)
        return self.createEntity(cmd, **kwargs)

    def getByRecordIds(self, *rids):
        ridStr = ",".join(
            [rid if rid.startswith("#") else "#" + rid for rid in rids])
        return self.client.command("select from [{}]".format(ridStr))

    def getAddedNymEdge(self, nym):
        nymEdge = self.client.command("select from {} where {} = '{}'".
                                      format(Edges.AddedNym, NYM, nym))
        if not nymEdge:
            return None
        else:
            return nymEdge[0]

    def _classesNeeded(self):
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

    def bootstrap(self):
        for cls, clbk in self._classesNeeded():
            if not self.classExists(cls):
                logger.debug("Creating class {}".format(cls))
                clbk()
            else:
                logger.debug("Class {} already exists".format(cls))

        # if not self.classExists(Vertices.Steward):
        #     self.createStewardClass()
        #
        # if not self.classExists(Vertices.Sponsor):
        #     self.createSponsorClass()
        #
        # if not self.classExists(Vertices.User):
        #     self.createUserClass()
        #

    def addSteward(self, txnId, nym, frm=None):
        # Add the steward
        if not frm:
            self.createVertex(Vertices.Steward, nym=nym, TXN_ID=txnId)
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
            self.createEdge(Edges.AddedNym, frm, to, TXN_ID=txnId,
                            ROLE=STEWARD, NYM=nym)

    def addSponsor(self, txnId, nym, frm):
        # Add the sponsor
        self.createVertex(Vertices.Sponsor, nym=nym, frm=frm)

        # Now add an edge from steward to sponsor, since only
        # a steward can create a sponsor
        frm = "(select from {} where {} = '{}')".format(Vertices.Steward, NYM, frm)
        to = "(select from {} where {} = '{}')".format(Vertices.Sponsor, NYM, nym)
        # Let there be an error in edge creation if `frm` does not exist
        # because if system is behaving correctly then `frm` would exist
        self.createEdge(Edges.AddedNym, frm, to, TXN_ID=txnId,
                        ROLE=SPONSOR, NYM=nym)

    # TODO: Consider if sponsors or stewards would have aliases too
    def addUser(self, txnId, nym, frm, reference=None):
        # Add the user
        self.createVertex(Vertices.User, nym=nym, frm=frm)

        # # TODO: After implementing agents, check if `frm` is agent
        # sponsor = self.client.command("select * from {} where {} = '{}'".
        #                               format(Vertices.Sponsor, NYM, frm))
        # if not sponsor:
        #     steward = self.client.command("select * from {} where {} = '{}'".
        #                                   format(Vertices.Steward, NYM, frm))
        #     if not steward:
        #         raise ValueError("frm should either be a sponsor or steward")
        #     else:
        #         typ = Vertices.Steward
        # else:
        #     typ = Vertices.Sponsor
        typ = self.getRole(frm)
        # Now add an edge from SPONSOR to USER
        frm = "(select from {} where {} = '{}')".format(typ, NYM, frm)
        to = "(select from {} where {} = '{}')".format(Vertices.User, NYM, nym)
        # Let there be an error in edge creation if `frm` does not exist
        # because if system is behaving correctly then `frm` would exist
        self.createEdge(Edges.AddedNym, frm, to, TXN_ID=txnId,
                        ROLE=USER, NYM=nym)
        if typ == Vertices.Sponsor:
            self.createEdge(Edges.Sponsors, frm, to, TXN_ID=txnId)

    def addAttribute(self, frm, to, data, txnId):
        attrVertex = self.createVertex(Vertices.Attribute, data=data)

        # if self.hasSponsor(frm):
        #     frm = "(select from {} where {} = '{}')".format(Vertices.Sponsor, NYM, frm)
        # elif self.hasSteward(frm):
        #     frm = "(select from {} where {} = '{}')".format(Vertices.Steward, NYM, frm)

        frm = "(select from {} where {} = '{}')".format(Vertices.Nym, NYM,
                                                        frm)
        self.createEdge(Edges.AddedAttribute, frm, attrVertex._rid,
                        TARGET_NYM=to, TXN_ID=txnId)

        # to = "(select from {} where {} = '{}')".format(Vertices.User, NYM, to)
        to = "(select from {} where {} = '{}')".format(Vertices.Nym, NYM,
                                                       to)
        self.createEdge(Edges.HasAttribute, to, attrVertex._rid, TXN_ID=txnId)

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
        # return any([func(nym) for func in (
        #     self.hasUser, self.hasSponsor, self.hasSteward)])
        return bool(self.getNym(nym))

    def getRole(self, nym):
        # # Querying in the order of probability of finding the nym
        # if self.hasUser(nym):
        #     return USER
        # elif self.hasSponsor(nym):
        #     return SPONSOR
        # elif self.hasSteward(nym):
        #     return STEWARD
        # else:
        #     return None

        # nymEdge = self.getAddedNymEdge(nym)
        # if not nymEdge:
        #     raise ValueError("Nym does not exist")
        # nymV, = self.getByRecordIds(nymEdge['in'].get())
        # nymCls = nymV._class
        # if nymCls == Vertices.User:
        #     return USER
        # elif nymCls == Vertices.Sponsor:
        #     return SPONSOR
        # elif nymCls == Vertices.Steward:
        #     return STEWARD
        # else:
        #     raise ValueError("Cannot determine role from {}".format(nymCls))
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
            frm, to = self.getByRecordIds(nymEdge['out'].get(), nymEdge['in'].get())
            result[ORIGIN] = frm.oRecordData.get(NYM)
            result[TARGET_NYM] = to.oRecordData.get(NYM)
            return result
