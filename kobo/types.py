# -*- coding: utf-8 -*-


__all__ = (
    "Enum",
    "EnumItem",
    "State",
    "StateEnum",
    "DictSet",
)


class EnumItem(object):
    """Data wrapper for Enum."""
    __slots__ = (
        "name",
        "help_text",
        "options",
    )

    def __init__(self, name, help_text=None, **kwargs):
        self.name = name
        self.help_text = help_text or ""
        self.options = kwargs


    def __str__(self):
        return self.name


    def __repr__(self):
        return str(self)


    def __eq__(self, obj):
        return str(self) == str(obj)


    def __getitem__(self, name):
        return self.options[name]


    def get(self, name, default=None):
        return self.options.get(name, default)


class Enum(object):
    """Enumerated list."""
    __slots__ = (
        "_dict",
        "_order",
        "_items",
    )


    def __init__(self, *args):
        """
        @param args: items to be enumerated
        @type args: str, EnumItem
        """
        self._items = []
        self._order = []

        # TODO: duplicity!
        for i in args:
            if not issubclass(type(i), EnumItem):
                i = EnumItem(str(i))
            if i in self._order:
                raise ValueError("Duplicite item: %s" % i)
            self._items.append(i)
            self._order.append(str(i))

        self._dict = dict([ (value, i) for i, value in enumerate(self._order) ])


    def __iter__(self):
        return iter(self._order)


    def __getitem__(self, key):
        if type(key) in (int, slice):
            return self._order[key]
        return self._dict[key]


    def get(self, key, default=None):
        try:
            return self[key]
        except (IndexError, KeyError):
            return default


    def get_num(self, key, default=None):
        try:
            return self._dict[key]
        except (IndexError, KeyError):
            return default


    def get_value(self, key, default=None):
        try:
            return self._order[key]
        except (IndexError, KeyError):
            return default


    def get_mapping(self):
        """Return list of (key, value) mappings."""
        return [ (self._dict[key], key) for key in self._order ]


    def get_item(self, key):
        if type(key) is int:
            return self._items[key]
        elif isinstance(key, State):
            return key
        elif isinstance(key, StateEnum):
            return self._current_state
        return self._items[self._dict[key]]


    def get_item_help_text(self, key):
        """Return item's help text."""
        return self.get_item(key).help_text


    def get_item_option(self, key, option, default=None):
        """Return item's option passed as a kwarg in it's constructor."""
        return self.get_item(key).get(option, default)


'''
class EnumItem(object):
    """Data wrapper for Enum."""
    __slots__ = (
        "name",
        "help_text",
        "options",
    )

    def __init__(self, name, help_text=None, **kwargs):
        self.name = name
        self.help_text = help_text or ""
        self.options = kwargs
'''

class State(EnumItem):
    __slots__ = (
        "next_states",
        "enter",
        "leave",
        "check_perms",
        "methods",
    )

    def __init__(self, name, next_states, help_text=None, enter=None, leave=None, check_perms=None, methods=None, **kwargs):
        """
        @param name: state name
        @type name:  str
        @param next_states: list of allowed state transitions
        @type next_states:  [str]
        @param help_text: help text associated to the state
        @type help_text:  str
        @param enter: list of functions to be executed on entering the state, they take (old_state, **kwargs) arguments
        @type enter:  [function]
        @param leave: list of functions to be executed on leaving the state, they take (old_state, **kwargs) arguments
        @type leave:  [function]
        @param methods:
        @type methods:  {"": }
        """

        EnumItem.__init__(self, name, help_text=help_text, **kwargs)
        self.next_states = next_states or []
        self.enter = enter or []
        self.leave = leave or []
        self.check_perms = check_perms or []
        self.methods = methods or {}


    def __getattr__(self, name):
        if name in self.methods:
            return self.methods[name]


class StateEnum(Enum):
    __slots__ = (
        "_current_state",
        "_to",
    )


    def __init__(self, *args):
        Enum.__init__(self, *args)
        self._current_state = None
        self._to = None

        # check if all states and transitions are sane
        all_next_states = set()
        for state in self._items:
            for next_state in state.next_states:
                 all_next_states.add(next_state)
        for state in all_next_states:
            if state not in self._items:
                 raise ValueError("State '%s' is not defined. Available states: %s" % (state, sorted(self._items)))


    def __str__(self):
        if self._current_state is None:
            return ""
        return str(self.get_state_id())
#        return self._current_state.name


    def set_state(self, state):
        self._current_state = self.get_item(state)


    def get_state(self):
        return self._current_state


    def get_state_id(self):
        return self.get_num(self._current_state.name)


    def get_final_states(self, return_id_list=False):
        result = []
        for state in self._items:
            if state.next_states:
                continue
            if return_id_list:
                result.append(self.get_num(state.name))
            else:
                result.append(state.name)
        return result


    def get_next_states_mapping(self, append_current=True, user=None, **kwargs):
        states = set()
        current_state = self._current_state.name

        if self._current_state is None:
            return []

        if append_current:
            states.add(current_state)
        states |= set(self._current_state.next_states)

        if user is not None:
            invalid_states = set()
            check_perms_args = dict(transition=True, user=user)
            check_perms_args.update(kwargs)

            for new_state in states:
                if new_state == current_state:
#                    valid_states.append(state)
                    continue

                # check permissions: all must be valid
                for func in self._current_state.check_perms:
                    if not func(current_state, new_state, **check_perms_args):
                        invalid_states.add(new_state)
                        break

            states -= invalid_states

        return sorted([(self.get_num(name), name) for name in states])


    def change_state(self, new_state, commit = True, **kwargs):
        '''new_state is number or state_name
           if commit is set, state is changed,
           otherwise transition is just tested and prepared
           commit with new_state == None just makes prepared transition if
           there is any, otherwise raises exception

           All callbacks are called with 'commit' parameter, to make
           side-effects just once

           returns: True if change was commited, False if not or no change
           was made (same new state, no new state)

           raises:
               ValueError:
                   - for invalid permissions
                   - invalid transitions
                   - commiting not prepared transition
        '''
        if new_state:
            new_state = self.get_item(new_state)
        if new_state == self._current_state or (new_state is None and not commit):
            return False
        if new_state is None and (not commit or self._to is None):
            raise ValueError('No new state set and commit specified')
        if new_state is None:
            new_state = self._to

        current_state = self._current_state.name
        #new_state = self.get_value(new_state)
        if str(new_state) not in self._current_state.next_states:
            raise ValueError("Invalid transition '%s' -> '%s'." % (current_state, new_state))

        # check transition permissions
        # if username is needed check_perms functions, pass it through kwargs
        check_perms_args = dict(commit=commit)
        check_perms_args.update(kwargs)
        for func in self._current_state.check_perms:
            if not func(current_state, new_state, **check_perms_args):
                raise ValueError("Insufficient rights for transition '%s' -> '%s'." % (current_state, new_state))

        # run "leave" functions on current state
        for func in self._current_state.leave:
            func(current_state, new_state, **kwargs)

        # run "enter" functions on new state
        for func in new_state.enter:
            func(current_state, new_state, **kwargs)

        if commit:
            self.set_state(new_state)
            self._to = None
            return True
        else:
            self._to = new_state
        return False


class DictSet(dict):
    """Dictionary with set operations on keys."""


    def copy(self):
        return DictSet(super(DictSet, self).copy())


    def __sub__(self, other):
        result = DictSet()
        for key, value in self.iteritems():
            if key not in other:
                result[key] = value
        return result


    def __or__(self, other):
        result = self.copy()
        result.update(other)
        return result


    def __and__(self, other):
        result = DictSet()
        for key, value in self.iteritems():
            if key in other:
                result[key] = value
        return result


    def add(self, key, value):
        # return True if a new key was added
        if key in self:
            return False
        self[key] = value
        return True


    def remove(self, key):
        del self[key]
