import django

def django_version_ge(version_str):
    """
    Check if current django is in higher or equal version than specified by
    version_str parameter
    """

    ver1 = [int(x) for x in django.get_version().split('.')]
    ver2 = [int(x) for x in version_str.split('.')]

    # lists must have the same lenght for comparison to work
    max_len = max(len(ver1), len(ver2))

    def append_zeros(lst):
        while len(lst) != max_len:
            lst.append(0)

    append_zeros(ver1)
    append_zeros(ver2)

    return ver1 >= ver2
