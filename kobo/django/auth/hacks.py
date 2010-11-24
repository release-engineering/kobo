# -*- coding: utf-8 -*-


import django.forms
import django.contrib.auth.forms
import django.contrib.auth.models
from django.utils.translation import ugettext_lazy as _
from django.core import validators


# extend username max_length to 255
MAX_LENGTH = 255
username_field = django.contrib.auth.models.User._meta.get_field_by_name("username")[0]
username_field.max_length = MAX_LENGTH
username_field.validators = []
username_field.validators.append(validators.MaxLengthValidator(MAX_LENGTH))
del username_field

user_re = r"^[\/\-\.\w]+$"
help_text = _("Required. %s characters or fewer. Alphanumeric characters only (letters, digits, underscores and slashes)." % MAX_LENGTH)
error_message = _("This value must contain only letters, numbers, underscores and slashes.")


class UserCreationForm(django.contrib.auth.forms.UserCreationForm):
    username = django.forms.RegexField(
        label=_("Username"),
        max_length=MAX_LENGTH,
        regex=user_re,
        help_text = help_text,
        error_message = error_message,
    )

    def save(self, commit=True):
        user = django.forms.ModelForm.save(self, commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(django.contrib.auth.forms.UserChangeForm):
    username = django.forms.RegexField(
        label=_("Username"),
        max_length=MAX_LENGTH,
        regex=user_re,
        help_text = help_text,
        error_message = error_message,
    )

    def __init__(self, *args, **kwargs):
        django.forms.ModelForm.__init__(self, *args, **kwargs)
        f = self.fields.get('user_permissions', None)
        if f is not None:
            f.queryset = f.queryset.select_related('content_type')


django.contrib.auth.forms.UserCreationForm = UserCreationForm
django.contrib.auth.forms.UserChangeForm = UserChangeForm
