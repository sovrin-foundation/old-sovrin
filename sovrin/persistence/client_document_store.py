from plenum.common.types import f
from plenum.common.util import getlogger
from sovrin.common.txn import TXN_ID, TXN_TIME, TARGET_NYM, TXN_TYPE
from plenum.persistence.client_document_store \
    import ClientDocumentStore as PlenumClientDS

logger = getlogger()

REQ_DATA = "ReqData"
ATTR_DATA = "AttrData"
LAST_TXN_DATA = "LastTxnData"


class ClientDocumentStore(PlenumClientDS):

    def classesNeeded(self):
        return [
            (ATTR_DATA, self.createAttributeClass),
            (REQ_DATA, self.createReqDataClass),
            (LAST_TXN_DATA, self.createLastTxnClass)
        ]

    def createAttributeClass(self):
        self.client.command("create class {}".format(ATTR_DATA))
        self.store.createClassProperties(ATTR_DATA, {
            TARGET_NYM: "string",
            "name": "string",
            "value": "string",
            "skey": "string"
        })
        self.store.createIndexOnClass(ATTR_DATA, TARGET_NYM)

    def createReqDataClass(self):
        self.client.command("create class {}".format(REQ_DATA))
        self.store.createClassProperties(REQ_DATA, {
            f.REQ_ID.nm: "long",
            f.IDENTIFIER.nm: "string",
            "acks": "embeddedset string",
            "nacks": "embeddedmap string",
            "replies": "embeddedmap string",
            TXN_TYPE: "string",
            TXN_ID: "string",
            TXN_TIME: "datetime",
            "serialNo": "long",
            "STH": "string",
            "auditPath": "embeddedlist string",
            "attribute": "embedded {}".format(ATTR_DATA),
            "consensed": "boolean"
        })
        self.store.createUniqueIndexOnClass(REQ_DATA, TXN_ID)
        self.store.createUniqueIndexOnClass(REQ_DATA, "serialNo")
        self.store.createIndexOnClass(REQ_DATA, "consensed")

    def getAllAttributeRequestsForNym(self, nym, identifier=None):
        whereClause = "attribute.{} = '{}'". \
            format(TARGET_NYM, nym)
        if identifier:
            whereClause += " and {} = '{}'".format(f.IDENTIFIER.nm, identifier)
        cmd = "select from {} where {} order by {} desc". \
            format(REQ_DATA, whereClause, TXN_TIME)
        # TODO: May be can use a better sql query using group by attribute name
        # and getting last attribute request of each group
        result = self.client.command(cmd)
        attributeReqs = {}  # Dict[str, Dict]
        for r in result:
            data = r.oRecordData
            if "attribute" in data and data["attribute"]["name"] \
                    not in attributeReqs:
                attributeReqs[data["attribute"]["name"]] = data
        return attributeReqs


