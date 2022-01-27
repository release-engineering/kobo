from copy import copy

import json
import six
from django.db import models
from django.core import exceptions
from django.utils.text import capfirst
from django.forms.widgets import Select
from django.forms.fields import CallableChoiceIterator

import kobo.django.forms
from kobo.types import StateEnum
from kobo.django.compat import gettext_lazy as _


'''
StateEnumField
==============

encapsulates StateEnum from kobo.types for use with django db and forms
layer.

Simply create model containing these fields and supply state engine instance
as parameter:

class MyModel(models.Model):
    state = StateEnumField(state_engine, default="NEW")

You can use such field as normal StateEnum. If model.save() is called, then
StateEnumFields will call change_state(None, True) if new state is prepared.


JSONField
=========

creates field which contains any JSON-codable object (via json.dumps). On
db level it is saved as a TextField.

There is boolean option "human_readable" which uses indent and sorting of
keys when saving to db. It is better for inspection, but can take significant
amount of space in some cases due to additional spaces and newlines. Also it
can slow down saving process, as keys are being sorted. From these reasons is
default value set to False.
'''

class StateEnumField(models.IntegerField):
    '''StateEnum DB encapsulation'''
    widget = Select

    def __init__(self, state_machine, *args, **kwargs):
        super(StateEnumField, self).__init__(*args, **kwargs)
        self.state_machine = state_machine
        self.widget = Select
        if self.has_default:
            self.state_machine.set_state(self.default)

    def _get_val_from_obj(self, obj):
        if obj:
            return getattr(obj, self.attname)
        else:
            return self.get_default()

    def from_db_value(self, value, expression, connection, context=None):
        if value is None:
            return None

        if isinstance(value, (str, six.text_type)) and not value.isdigit():
            value = self.state_machine.get_num(value)

        try:
            value = int(value)
            if value < 0:
                raise ValueError
        except (TypeError, ValueError):
            raise exceptions.ValidationError(_("This value must be a positive integer."))

        state_machine = copy(self.state_machine)
        state_machine.set_state(state_machine.get_value(value))
        return state_machine

    def to_python(self, value):
        if value is None:
            return None

        if isinstance(value, StateEnum):
            return value

        if isinstance(value, (str, six.text_type)) and not value.isdigit():
            value = self.state_machine.get_num(value)

        try:
            value = int(value)
            if value < 0:
                raise ValueError
        except (TypeError, ValueError):
            raise exceptions.ValidationError(_("This value must be a positive integer."))

        state_machine = copy(self.state_machine)
        state_machine.set_state(state_machine.get_value(value))
        return state_machine


    def _get_choices(self):
        return tuple(self.state_machine.get_next_states_mapping(current=self.state_machine.get_state_id()))
    
    def _set_choices(self, value):
        # Setting choices also sets the choices on the widget.
        # choices can be any iterable, but we call list() on it because
        # it will be consumed more than once.
        if callable(value):
            value = CallableChoiceIterator(value)
        elif value is not None:
            value = list(value)
        else:
            value = []

        self._choices = self.widget.choices = value

    choices = property(_get_choices, _set_choices)


    def get_db_prep_value(self, value, connection, prepared=False):
        if value is not None:
            try:
                value = self.state_machine.get_value(value)
            except:
                value = str(value._current_state)

#        self.state_machine.change_state(value, commit=False)
        if value is None:
            return None
        return self.state_machine.get_num(value)


    def get_db_prep_save(self, value, connection):
        return self.get_db_prep_value(value, connection=connection)


    def pre_save(self, instance, add):
        state = getattr(instance, self.attname)
        if state._to is not None:
            state.change_state(None, commit=True)
        return state


    def formfield(self, form_class=kobo.django.forms.StateChoiceFormField, **kwargs):
        # after fix of http://code.djangoproject.com/ticket/9245 could be
        # simplified
        defaults = {'required': not self.blank, 'label': capfirst(self.verbose_name), 'help_text': self.help_text}
        if self.has_default():
            defaults['initial'] = self.get_default()
            if callable(self.default):
                defaults['show_hidden_initial'] = True
        # Fields with choices get special treatment.
        include_blank = self.blank or not (self.has_default() or 'initial' in kwargs)
        defaults['choices'] = self.get_choices(include_blank=include_blank)
        defaults['coerce'] = self.to_python
        if self.null:
            defaults['empty_value'] = None
        # Many of the subclass-specific formfield arguments (min_value,
        # max_value) don't apply for choice fields, so be sure to only pass
        # the values that TypedChoiceField will understand.
        for k in kwargs.keys():
            if k not in ('coerce', 'empty_value', 'choices', 'required',
                         'widget', 'label', 'initial', 'help_text',
                         'error_messages'):
                del kwargs[k]
        defaults.update(kwargs)
        return form_class(**defaults)


class JSONField(models.TextField):
    """JSON field for storing a serialized dictionary or list."""

    def __init__(self, *args, **kwargs):
        self.human_readable = kwargs.pop('human_readable', False)
        return super(JSONField, self).__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        if not isinstance(value, six.string_types):
            return value

        try:
            return json.loads(value)
        except ValueError:
            raise exceptions.ValidationError(_("Cannot deserialize JSON data. '%s'") % value)

    def to_python(self, value):
        if value is None:
            return None

        if not isinstance(value, six.string_types):
            return value

        try:
            return json.loads(value)
        except ValueError:
            raise exceptions.ValidationError(_("Cannot deserialize JSON data. '%s'") % value)

    def get_db_prep_value(self, value, *args, **kwargs):
        if value is None or value == "null":
            return None
        try:
            if self.human_readable:
                return json.dumps(value, indent=2, sort_keys=True)
            else:
                return json.dumps(value)
        except Exception:
            raise exceptions.ValidationError(_("Cannot serialize JSON data."))

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_db_prep_value(value)

    def value_from_object(self, obj):
        if self.human_readable:
            return json.dumps(super(JSONField, self).value_from_object(obj), indent=2, sort_keys=True)
        else:
            return json.dumps(super(JSONField, self).value_from_object(obj))

    def formfield(self, form_class=kobo.django.forms.JSONFormField, **kwargs):
        kwargs["form_class"] = form_class
        return super(JSONField, self).formfield(**kwargs)


# HACK:
import django.contrib.admin.options
django.contrib.admin.options.FORMFIELD_FOR_DBFIELD_DEFAULTS[JSONField] = {"widget": kobo.django.forms.JSONWidget}
