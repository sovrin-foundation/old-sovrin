from plenum.common.log import getlogger
from sovrin.common.txn import STEWARD, SPONSOR, OWNER, TGB
from sovrin.common.txn import TRUSTEE


logger = getlogger()


class Authoriser:
    AuthMap = {
        'NYM_role__TRUSTEE': {TRUSTEE: [], },
        'NYM_role__TGB': {TRUSTEE: [], },
        'NYM_role__STEWARD': {TRUSTEE: [], STEWARD: []},
        'NYM_role__SPONSOR': {TRUSTEE: [], STEWARD: []},
        'NYM_role__': {TRUSTEE: [], TGB: [], STEWARD: [], SPONSOR: []},
        'NYM_role_TRUSTEE_': {TRUSTEE: []},
        'NYM_role_TGB_': {TRUSTEE: []},
        'NYM_role_STEWARD_': {TRUSTEE: []},
        'NYM_role_SPONSOR_': {TRUSTEE: []},
        'NODE_services__[VALIDATOR]': {STEWARD: [OWNER, ]},
        'NODE_services_[VALIDATOR]_[]': {TRUSTEE: [], STEWARD: [OWNER, ]},
        'POOL_UPGRADE_action__start': {TRUSTEE: [], TGB: []},
        'POOL_UPGRADE_action_start_cancel': {TRUSTEE: [], TGB: []}
    }

    @staticmethod
    def isValidRole(role) -> bool:
        return role in (TRUSTEE, TGB, STEWARD, SPONSOR, None)

    @staticmethod
    def authorised(typ, field, actorRole, oldVal=None, newVal=None,
                   isActorOwnerOfSubject=None) -> (bool, str):
        oldVal = '' if oldVal is None else \
            str(oldVal).replace('"', '').replace("'", '')
        newVal = '' if newVal is None else \
            str(newVal).replace('"', '').replace("'", '')
        key = '_'.join([typ, field, oldVal, newVal])
        if key not in Authoriser.AuthMap:
            msg = 'Cannot create key from {} {} {} {}'.\
                format(typ, field, oldVal, newVal)
            logger.error(msg)
            return False, msg
        roles = Authoriser.AuthMap[key]
        if actorRole not in roles:
            return False, '{} not in allowed roles {}'.format(actorRole, roles)
        roleDetails = roles[actorRole]
        if len(roleDetails) == 0:
            return True, ''
        else:
            r = OWNER in roleDetails and isActorOwnerOfSubject
            msg = '' if r else 'Only owner is allowed'
            return r, msg
