try:
    # Ancient case: ugettext is the unicode-aware variant
    from django.utils.translation import ugettext_lazy as gettext_lazy
except ImportError:
    # Modern (py3-only) case
    from django.utils.translation import gettext_lazy


try:
    # Ancient case: force_text is the unicode-aware variant
    from django.utils.encoding import force_text as force_str
except:
    # Modern (py3-only) case
    from django.utils.encoding import force_str


__all__ = ["gettext_lazy", "force_str"]
