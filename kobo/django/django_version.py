import django
from distutils.version import LooseVersion

def django_version_ge(version_str):
    """
    Check if current django is in higher or equal version than specified by
    version_str parameter
    """

    return LooseVersion(django.get_version()) >= LooseVersion(version_str)
