# -*- coding: utf-8 -*-


import django.forms
import django.contrib.auth.forms
import django.contrib.auth.models
from django.utils.translation import ugettext_lazy as _


# extend username max_length to 255
django.contrib.auth.models.User._meta.get_field_by_name("username")[0].max_length = 255


user_re = r"^[\/\-\.\w]+$"
help_text = _("Required. 255 characters or fewer. Alphanumeric characters only (letters, digits, underscores and slashes).")
error_message = _("This value must contain only letters, numbers, underscores and slashes.")


class UserCreationForm(django.contrib.auth.forms.UserCreationForm):
    username = django.forms.RegexField(
        label=_("Username"),
        max_length=255,
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
        max_length=255,
        regex=user_re,
        help_text = help_text,
        error_message = error_message,
    )


django.contrib.auth.forms.UserCreationForm = UserCreationForm
django.contrib.auth.forms.UserChangeForm = UserChangeForm
