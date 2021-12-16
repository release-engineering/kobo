# -*- coding: utf-8 -*-

import six
try:
    import json
except ImportError:
    import simplejson as json

import django.forms.fields
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape
try:
    from django.forms.utils import flatatt
except ImportError:
    from django.forms.util import flatatt

from kobo.django.compat import gettext_lazy as _, force_str


class StateChoiceFormField(django.forms.fields.TypedChoiceField):
    '''
    def __init__(self, *args, **kwargs):
        super(StateChoiceFormField, self).__init__(*args, **kwargs)
         ugly hack - get back reference to StateEnum object
        state = kwargs['coerce'].__self__
        print 'initscff', kwargs['initial'], state, state.choices
        print type(kwargs['initial'])
    '''

    def clean(self, value):
        value = super(StateChoiceFormField, self).clean(value)
        try:
            value = int(str(value))
        except ValueError:
            raise ValidationError('Wrong state value.')
        self.widget.choices = self.choices
        if value in django.forms.fields.EMPTY_VALUES:
            return None
        for c in self.choices:
            if c[0] == value:
                return c[1]
        raise ValidationError('Selected value is not in valid choices.')


class JSONWidget(django.forms.widgets.Textarea):
    def render(self, name, value, attrs=None, renderer=None):
        if value is None: value = ''
        final_attrs = self.build_attrs(attrs, name=name)

        if not isinstance(value, six.string_types):
            value = json.dumps(value)

        return mark_safe(u'<textarea%s>%s</textarea>' % (flatatt(final_attrs),
                conditional_escape(force_str(value))))


class JSONFormField(django.forms.fields.CharField):
    widget = JSONWidget

    def from_db_value(self, value, expression, connection, context=None):
        return self.to_python(value)


    def to_python(self, value):
        try:
            result = json.loads(value)
        except ValueError:
            raise ValidationError(_("Cannot deserialize JSON data."))
        else:
            if not isinstance(result, (dict, list)):
                raise ValidationError(_("Data types are restricted to JSON serialized dict or list only."))
            return result
