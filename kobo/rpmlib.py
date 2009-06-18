# -*- coding: utf-8 -*-


# Some code comes from koji: https://fedorahosted.org/koji/


import rpm
from kobo.shortcuts import hex_string


__all__ = (
    "get_rpm_header",
    "get_header_field",
    "get_header_fields",
    "split_nvr_epoch",
    "parse_nvr",
    "parse_nvra",
    "get_keys_from_header",
)


body_header_tags = ["siggpg", "sigpgp"]
head_header_tags = ["dsaheader", "rsaheader"]


def get_rpm_header(f, ts=None):
    """Return the rpm header."""
    if ts is None:
        ts = rpm.TransactionSet()
        ts.setVSFlags(rpm._RPMVSF_NOSIGNATURES|rpm._RPMVSF_NODIGESTS)

    if type(f) in (str, unicode):
        fo = open(f, "r")
    else:
        fo = f

    hdr = ts.hdrFromFdno(fo.fileno())

    if fo is not f:
        fo.close()

    return hdr


def get_header_field(hdr, name):
    """Extract named field from an rpm header."""
    hdr_key = getattr(rpm, "RPMTAG_%s" % name.upper(), None)

    if hdr_key is None:
        raise AttributeError("No such rpm header field: %s" % name)

    return hdr[hdr_key]


def get_header_fields(hdr, fields):
    """Extract named fields from an rpm header and return as a dictionary.
    Hdr may be either the rpm header or the rpm filename.
    """

    result = {}
    for field in fields:
        result[field] = get_header_field(hdr, field)
    return result


def split_nvr_epoch(nvre):
    """Split N-V-R:E or E:N-V-R to (N-V-R, E)."""
    if ":" in nvre:
        if nvre.count(":") != 1:
            raise ValueError("Invalid NVRE: %s" % nvre)

        nvr, epoch = nvre.rsplit(":", 1)
        if "-" in epoch:
            if "-" not in nvr:
                # switch nvr with epoch
                nvr, epoch = epoch, nvr
            else:
                # it's probably N-E:V-R format, handle it after the split
                nvr, epoch = nvre, ""
    else:
        nvr, epoch = nvre, ""

    return (nvr, epoch)


def parse_nvr(nvre):
    """Split N-V-R into dictionary of data."""
    nvr, epoch = split_nvr_epoch(nvre)

    nvr_parts = nvr.rsplit("-", 2)
    if len(nvr_parts) != 3:
        raise ValueError("Invalid NVR: %s" % nvr)

    # parse E:V
    if epoch == "" and ":" in nvr_parts[1]:
        epoch, nvr_parts[1] = nvr_parts[1].split(":", 1)

    # check if epoch is empty or numeric
    if epoch != "":
        try:
            int(epoch)
        except ValueError:
            raise ValueError("Invalid epoch '%s' in '%s'" % (epoch, nvr))

    result = dict(zip(["name", "version", "release"], nvr_parts))
    result["epoch"] = epoch
    return result


def parse_nvra(nvra):
    """Split N-V-R.A.rpm into dictionary of data."""

    epoch = ""
    for i in xrange(2):
        # run this twice to parse N-V-R.A.RPM:E and N-V-R.A:E.rpm
        if nvra.endswith(".rpm"):
            # strip .rpm suffix
            nvra = nvra[:-4]
        else:
            # split epoch (if exists)
            nvra, epoch = split_nvr_epoch(nvra)

    nvra_parts = nvra.rsplit(".", 1)
    if len(nvra_parts) != 2:
        raise ValueError("Invalid NVRA: %s" % nvra)

    nvr, arch = nvra_parts
    result = parse_nvr(nvr)
    result["arch"] = arch
    result["src"] = (arch == "src")
    if epoch != "":
        result["epoch"] = epoch
    return result


def make_nvr(nvrea_dict, add_epoch=False):
    """Make N-V-R from a nvrea dictionary."""
    if add_epoch:
        epoch = nvrea_dict.get("epoch", "")
        if epoch != "":
            epoch = "%s:" % epoch
    else:
        epoch = ""

    return "%s%s-%s-%s" % (epoch, nvrea_dict["name"], nvrea_dict["version"], nvrea_dict["release"])


def make_nvra(nvrea_dict, add_epoch=False, add_rpm=False):
    """Make N-V-R.A from a nvrea dictionary."""
    result = "%s.%s" % (make_nvr(nvrea_dict, add_epoch), nvrea_dict["arch"])
    if add_rpm:
        result += ".rpm"
    return result


def make_nvrea_list(nvrea_dict):
    """Make [N, V, R, E, A] list from a nvrea dictionary."""
    return [ nvrea_dict[i] for i in ("name", "version", "release", "epoch", "arch") ]


def compare_nvr(nvr_dict1, nvr_dict2, ignore_epoch=False):
    """Compare two N-V-R dictionaries."""
    nvr1 = nvr_dict1.copy()
    nvr2 = nvr_dict2.copy()

    if nvr1["name"] != nvr2["name"]:
        raise ValueError("Package names doesn't match: %s, %s" % (nvr1["name"], nvr2["name"]))

    if ignore_epoch:
        nvr1["epoch"] = 0
        nvr2["epoch"] = 0

    if nvr1["epoch"] is None:
        nvr1["epoch"] = ""

    if nvr2["epoch"] is None:
        nvr2["epoch"] = ""

    return rpm.labelCompare((str(nvr1["epoch"]), nvr1["version"], nvr1["release"]), (str(nvr2["epoch"]), nvr2["version"], nvr2["release"]))


def get_keys_from_header(hdr):
    """Extract signing key id from a rpm header."""
    result = []
    head_keys = []

    for field in head_header_tags:
        sigkey = get_header_field(hdr, field)
        if sigkey:
            head_keys.append(hex_string(sigkey[13:17]))

    for field in body_header_tags:
        sigkey = get_header_field(hdr, field)
        if sigkey:
            key_id = hex_string(sigkey[13:17])
            if key_id in head_keys:
                result.append(key_id)
            else:
                raise ValueError("%s key not found in head keys: %s" % (field, key_id))

    if len(result) > 1:
        raise ValueError("More than one key found: %s" % result)

    if len(result) == 1:
        return result[0]
