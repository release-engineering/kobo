import six

if six.PY2:
    # Ancient cases: force_text and ugettext are the unicode-aware variants
    from django.utils.translation import ugettext_lazy as gettext_lazy
    from django.utils.encoding import force_text as force_str
else:
    # Modern (py3-only) case
    from django.utils.translation import gettext_lazy
    from django.utils.encoding import force_str


__all__ = ["gettext_lazy", "force_str"]
