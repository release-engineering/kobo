from django.forms import fields
from django.core.exceptions import ValidationError

class StateChoiceFormField(fields.TypedChoiceField):
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
        if value in fields.EMPTY_VALUES:
            return None
        for c in self.choices:
            if c[0] == value:
                return c[1]
        raise ValidationError('Selected value is not in valid choices.')
