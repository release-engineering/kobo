from __future__ import absolute_import
from kobo.types import State, StateEnum

def perm_new(*args, **kwargs):
    return True

def perm_on_review(**kwargs):
    user = kwargs.get('user')
    return user.has_perm('pkg.verify')

def perm_verified(**kwargs):
    user = kwargs.get('user')
    next = kwargs.get('new_state', None)
    if next == 'REJECTED' or next == 'ACCEPTED':
        return user.has_perm('pkg.accept')
    elif next == 'ON_REVIEW':
        return user.has_perm('pkg.revert')
    else:
        raise ValueError('Wrong transition')

def perm_change_reviewer(user, state = None):
    return user.has_perm('pkg.change_reviewer')

def perm_edit_rest(user):
    return user.groups.filter(name = 'Reviewers').count() != 0 or user.is_superuser

workflow = StateEnum(
    State(
        name = "NEW",
        next_states = ["ON_REVIEW"],
        check_perms = [perm_new],
    ),
    State(
        name = "ON_REVIEW",
        next_states = ["VERIFIED"],
#        check_perms = [perm_on_review],
    ),
    State(
        name = "VERIFIED",
        next_states = ["REJECTED", "ACCEPTED", "ON_REVIEW"],
#        check_perms = [perm_verified],
    ),
    State(
        name = "REJECTED",
        next_states = None,
    ),
    State(
        name = "ACCEPTED",
        next_states = None,
    ),
)
