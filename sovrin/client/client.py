import json
from base64 import b64decode
from typing import Mapping, List, Any, Dict, Union, Tuple

import base58
from plenum.client.client import Client as PlenumClient
from plenum.client.signer import Signer
from plenum.common.request_types import OP_FIELD_NAME, Request
from plenum.common.stacked import HA
from plenum.common.txn import REQACK, REPLY, REQNACK
from plenum.common.util import getlogger, getMaxFailures, \
    getSymmetricallyEncryptedVal, libnacl

from sovrin.client.client_storage import ClientStorage
from sovrin.common.txn import TXN_TYPE, ADD_ATTR, DATA, TXN_ID, TARGET_NYM, SKEY, \
    DISCLOSE, NONCE, ORIGIN, GET_ATTR, GET_NYM, TXN_TIME

logger = getlogger()


class Client(PlenumClient):
    def __init__(self,
                 name: str,
                 nodeReg: Dict[str, HA]=None,
                 ha: Union[HA, Tuple[str, int]]=None,
                 lastReqId: int = 0,
                 signer: Signer=None,
                 signers: Dict[str, Signer]=None,
                 basedirpath: str=None):
        super().__init__(name,
                         nodeReg,
                         ha,
                         lastReqId,
                         signer,
                         signers,
                         basedirpath)
        self.storage = self.getStorage(basedirpath)
        self.lastReqId = self.storage.getLastReqId()
        # TODO: SHould i store values of attributes as non encrypted
        # Dictionary of attribute requests
        # Key is request id and values are stored as tuple of 5 elements
        # identifier, toNym, secretKey, attribute name, txnId
        self.attributeReqs = self.storage.loadAttributes()
        # type: Dict[int, List[Tuple[str, str, str, str, str]]]
        self.autoDiscloseAttributes = False

    def setupDefaultSigner(self):
        # Sovrin clients should use a wallet, which supplies the signers
        pass

    def getStorage(self, baseDirPath=None):
        return ClientStorage(self.name, baseDirPath)

    def submit(self, *operations: Mapping, identifier: str=None) -> List[Request]:
        keys = []
        attributeNames = []
        for op in operations:
            if op[TXN_TYPE] == ADD_ATTR:
                # Data is a json object with key as attribute name and value
                # as attribute value
                data = op[DATA]
                encVal, secretKey = getSymmetricallyEncryptedVal(data)
                op[DATA] = encVal
                keys.append(secretKey)
                anm = list(json.loads(data).keys())[0]
                attributeNames.append(anm)
        requests = super().submit(*operations, identifier=identifier)
        for r in requests:
            self.storage.addRequest(r)
            operation = r.operation
            # If add attribute transaction then store encyption key and
            # attribute name with the request id for the attribute
            if operation[TXN_TYPE] == ADD_ATTR:
                attrData = (r.identifier,
                            operation[TARGET_NYM],
                            keys.pop(0),
                            attributeNames.pop(0),
                            None)
                self.attributeReqs[r.reqId] = attrData
                self.storage.addAttribute(r.reqId, attrData)
        return requests

    def handleOneNodeMsg(self, wrappedMsg) -> None:
        super().handleOneNodeMsg(wrappedMsg)
        msg, sender = wrappedMsg
        if OP_FIELD_NAME not in msg:
            logger.error("Op absent in message {}".format(msg))
        elif msg[OP_FIELD_NAME] == REQACK:
            self.storage.addAck(msg, sender)
        elif msg[OP_FIELD_NAME] == REQNACK:
            self.storage.addNack(msg, sender)
        elif msg[OP_FIELD_NAME] == REPLY:
            result = msg['result']
            if self.autoDiscloseAttributes:
                # TODO: This is just for now. As soon as the client finds out
                # that the attribute is added it discloses it
                reqId = msg["reqId"]
                if reqId in self.attributeReqs and not self.attributeReqs[
                    reqId][-1]:
                    origin = self.attributeReqs[reqId][0]
                    key = self.attributeReqs[reqId][2]
                    txnId = result[TXN_ID]
                    self.attributeReqs[reqId] += (txnId, )
                    self.doAttrDisclose(origin, result[TARGET_NYM], txnId, key)
            self.storage.addReply(msg['reqId'], sender, result)
        else:
            logger.debug("Invalid op message {}".format(msg))

    def getTxnById(self, txnId: str):
        for v in self.storage.replyStore.iterator(include_key=False):
            result = self.storage.serializer.deserialize(v, orderedFields=self.storage.replyFields)
            if result[TXN_ID] == txnId:
                return result

    def getTxnsByNym(self, nym: str):
        # TODO Implement this
        pass

    def findTxns(self, keyName: str, keyValue: Any=None):
        def cond(result):
            return keyName in result and (keyValue is None or keyValue ==
                                          result[keyName])

        return self.getTxnsByCondition(condition=cond)

    def getTxnsByCondition(self, condition):
        # TODO: This is very inefficient. For a starting point store have a
        # keyspace partition for storing a map of cryptonyms(or txn types or
        # which attribute of interest) to reqIds

        results = {}        # type: Dict[int, Tuple[Set[str], Any])
        for k, v in self.storage.replyStore.iterator():
            result = self.storage.serializer.deserialize(
                v, orderedFields=self.storage.replyFields)
            if condition(result):
                reqId, sender = k.split('-')
                reqId = int(reqId)
                sender = sender
                if reqId not in results:
                    results[reqId] = (set(), result)
                results[reqId][0].add(sender)
                # TODO: What about different nodes sending different replies?
                #  Need to pick reply which is given by f+1 nodes. Having
                # hashes to check for equality might be efficient

        f = getMaxFailures(len(self.nodeReg))
        return [val[1] for rid, val in results.items() if len(val[0]) > f]

    def hasMadeRequest(self, reqId: int):
        return self.storage.hasRequest(reqId)

    def replyIfConsensus(self, reqId: int):
        f = getMaxFailures(len(self.nodeReg))
        replies, errors = self.storage.getAllReplies(reqId)
        r = list(replies.values())[0] if len(replies) > f else None
        e = list(errors.values())[0] if len(errors) > f else None
        return r, e

    # TODO: Just for now. Remove it later
    def doAttrDisclose(self, origin, target, txnId, key):
        box = libnacl.public.Box(b64decode(origin), b64decode(target))

        data = json.dumps({TXN_ID: txnId, SKEY: key})
        nonce, boxedMsg = box.encrypt(data.encode(), pack_nonce=False)

        op = {
            ORIGIN: origin,
            TARGET_NYM: target,
            TXN_TYPE: DISCLOSE,
            NONCE: base58.b58encode(nonce),
            DATA: base58.b58encode(boxedMsg)
        }
        self.submit(op, identifier=origin)

    def doGetAttributeTxn(self, identifier, attrName):
        op = {
            ORIGIN: identifier,
            TARGET_NYM: identifier,
            TXN_TYPE: GET_ATTR,
            # TODO: Need to encrypt get query
            DATA: json.dumps({"name": attrName})
        }
        self.submit(op, identifier=identifier)

    @staticmethod
    def _getDecryptedData(encData, key):
        data = bytes(bytearray.fromhex(encData))
        rawKey = bytes(bytearray.fromhex(key))
        box = libnacl.secret.SecretBox(rawKey)
        decData = box.decrypt(data).decode()
        return json.loads(decData)

    def getAttributeForNym(self, nym, attrName, identifier=None):
        reqId = None
        for rid, (idf, toNym, key, anm, tid) in self.attributeReqs.items():
            if nym == toNym and anm == attrName and \
                    (not identifier or idf == identifier):
                reqId = rid
                break
        if reqId is None:
            return None
        else:
            reply, error = self.replyIfConsensus(reqId)
            if reply is None:
                return None
            else:
                return self._getDecryptedData(reply[DATA], key)

    def getAllAttributesForNym(self, nym, identifier=None):
        requests = [(rid, key) for rid, (idf, toNym, key, anm, tid) in
                    self.attributeReqs.items()
                    if nym == toNym and (not identifier or idf == identifier)]

        attributes = {}
        for (rid, key) in requests:
            reply, error = self.replyIfConsensus(rid)
            if reply is not None:
                attr = self._getDecryptedData(reply[DATA], key)
                name, val = list(attr.items())[0]
                if name not in attributes:
                    attributes[name] = (val, reply[TXN_TIME])
                elif reply[TXN_TIME] > attributes[name][1]:
                    attributes[name] = (val, reply[TXN_TIME])

        attributes = [{attr: val} for attr, (val, tm) in attributes.items()]
        return attributes

    def doGetNym(self, identifier, nym):
        op = {
            ORIGIN: identifier,
            TARGET_NYM: nym,
            TXN_TYPE: GET_NYM,
        }
        self.submit(op, identifier=identifier)

    def hasNym(self, nym):
        for v in self.storage.replyStore.iterator(include_key=False):
            result = self.storage.serializer.deserialize(
                v, orderedFields=self.storage.replyFields)
            # If transaction is of GET_NYM type and the query was for the `nym`
            # and data was returned which here is `transaction_id`
            if result[TXN_TYPE] == GET_NYM and result[TARGET_NYM] == nym \
                    and result[DATA]:
                return True
        return False

    def isRequestSuccessful(self, reqId):
        acks = self.storage.getAcks(reqId)
        nacks = self.storage.getNacks(reqId)
        f = getMaxFailures(len(self.nodeReg))
        if len(acks) > f:
            return True, "Done"
        elif len(nacks) > f:
            # TODO: What if the the nacks were different from each node?
            return False, list(nacks.values())[0]
        else:
            return None
