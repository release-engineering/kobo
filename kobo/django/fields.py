from copy import copy

import django.utils.simplejson
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core import exceptions
from django.utils.text import capfirst

import kobo.django.forms
from kobo.types import StateEnum

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
'''

class StateEnumField(models.IntegerField):
    '''StateEnum DB encapsulation'''
    __metaclass__ = models.SubfieldBase


    def __init__(self, state_machine, *args, **kwargs):
        super(StateEnumField, self).__init__(*args, **kwargs)
        self.state_machine = state_machine
        if self.has_default:
            self.state_machine.set_state(self.default)

    def _get_val_from_obj(self, obj):
        if obj:
            return getattr(obj, self.attname)
        else:
            return self.get_default()


    def to_python(self, value):
        if value is None:
            return None

        if isinstance(value, StateEnum):
            return value

        if isinstance(value, (str, unicode)) and not value.isdigit():
            value = self.state_machine.get_num(value)

        try:
            value = int(value)
            if value < 0:
                raise ValueError
        except (TypeError, ValueError), ex:
            raise exceptions.ValidationError(_("This value must be a positive integer."))

        state_machine = copy(self.state_machine)
        state_machine.set_state(state_machine.get_value(value))
        return state_machine


    def _get_choices(self):
        return tuple(self.state_machine.get_next_states_mapping(current=self.state_machine.get_state_id()))
    choices = property(_get_choices, kobo.django.forms.StateChoiceFormField._set_choices)


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
    __metaclass__ = models.SubfieldBase

    def to_python(self, value):
        if value is None:
            return None

        if not isinstance(value, basestring):
            return value

        try:
            return django.utils.simplejson.loads(value)
        except ValueError:
            raise exceptions.ValidationError(_("Cannot deserialize JSON data."))

    def pre_save(self, model_instance, add):
        value = getattr(model_instance, self.attname, None)
        if value is None or value == "null":
            return None
        return django.utils.simplejson.dumps(value)

    def formfield(self, form_class=kobo.django.forms.JSONFormField, **kwargs):
        kwargs["form_class"] = form_class
        return super(JSONField, self).formfield(**kwargs)


# HACK:
import django.contrib.admin.options
django.contrib.admin.options.FORMFIELD_FOR_DBFIELD_DEFAULTS[JSONField] = {"widget": kobo.django.forms.JSONWidget}
