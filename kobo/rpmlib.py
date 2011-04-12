# -*- coding: utf-8 -*-


# Some code comes from koji: https://fedorahosted.org/koji/


import koji
import rpm
from kobo.shortcuts import hex_string


__all__ = (
    "FILE_DIGEST_ALGO_MAP",
    "compare_nvr",
    "get_rpm_header",
    "get_header_field",
    "get_header_fields",
    "split_nvr_epoch",
    "parse_nvr",
    "parse_nvra",
    "parse_evr",
    "get_keys_from_header",
    "get_digest_algo_from_header",
)


body_header_tags = ["siggpg", "sigpgp"]
head_header_tags = ["dsaheader", "rsaheader"]


FILE_DIGEST_ALGO_MAP = {
    1: "MD5",
    2: "SHA1",
    8: "SHA256",
    9: "SHA384",
    10: "SHA512",
}



def get_rpm_header(file_name, ts=None):
    """Read rpm header.

    @param file_name: rpm file name (or file object)
    @type file_name: str (or file)
    @param ts: transaction set instance
    @type ts: rpm.TransactionSet
    @return: rpm header
    @rtype: rpm.hdr
    """

    if ts is None:
        ts = rpm.TransactionSet()
        ts.setVSFlags(rpm._RPMVSF_NOSIGNATURES|rpm._RPMVSF_NODIGESTS)

    if type(file_name) in (str, unicode):
        fo = open(file_name, "r")
    else:
        fo = file_name

    hdr = ts.hdrFromFdno(fo.fileno())

    if fo is not file_name:
        fo.close()

    return hdr


def get_header_field(hdr, name):
    """Extract named field from a rpm header.

    @param hdr: a rpm header
    @type hdr: rpm.hdr
    @param name: a rpm field name
    @type name: str
    @return: value of a rpm field
    @rtype: str or list
    """

    if name == "arch":
        # HACK: return "src" or "nosrc" arch instead of build arch
        if get_header_field(hdr, "sourcepackage"):
            if get_header_field(hdr, "nosource"):
                return "nosrc"
            return "src"

    hdr_key = getattr(rpm, "RPMTAG_%s" % name.upper(), None)

    if hdr_key is None:
        # HACK: nosource is not in exported rpm tags
        if name == "nosource":
            return hdr[1051]
        raise AttributeError("No such rpm header field: %s" % name)

    return hdr[hdr_key]


def get_header_fields(hdr, fields):
    """Extract named fields from a rpm header and return as a dictionary.

    @param fields: rpm field names
    @type fields: list
    @rtype: dict
    """

    result = {}
    for field in fields:
        result[field] = get_header_field(hdr, field)
    return result


def split_nvr_epoch(nvre):
    """Split nvre to N-V-R and E.

    @param nvre: E:N-V-R or N-V-R:E string
    @type nvre: str
    @return: (N-V-R, E)
    @rtype: (str, str)
    """

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
    """Split N-V-R into a dictionary.

    @param nvre: N-V-R:E, E:N-V-R or N-E:V-R string
    @type nvre: str
    @return: {name, version, release, epoch}
    @rtype: dict
    """

    if "/" in nvre:
        nvre = nvre.split("/")[-1]

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
    """Split N-V-R.A[.rpm] into a dictionary.

    @param nvra: N-V-R:E.A[.rpm], E:N-V-R.A[.rpm], N-V-R.A[.rpm]:E or N-E:V-R.A[.rpm] string
    @type nvra: str
    @return: {name, version, release, epoch, arch}
    @rtype: dict
    """

    if "/" in nvra:
        nvra = nvra.split("/")[-1]

    epoch = ""
    for i in xrange(2):
        # run this twice to parse N-V-R.A.rpm:E and N-V-R.A:E.rpm
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
    if "-" in arch:
        raise ValueError("Invalid arch '%s' in '%s'" % (arch, nvra))

    result = parse_nvr(nvr)
    result["arch"] = arch
    result["src"] = (arch == "src")
    if epoch != "":
        result["epoch"] = epoch
    return result


def parse_evr(evr, allow_empty_release=False):
    """Split E:V-R into a dictionary."""

    if ":" in evr:
        epoch, vr = evr.split(":", 1)
        try:
            int(epoch)
        except ValueError:
            try:
                int(vr)
            except ValueError:
                raise ValueError("Invalid epoch in '%s'" % evr)
            epoch, vr = vr, epoch
    else:
        epoch, vr = ("", evr)

    if "-" in vr:
        version, release = vr.split("-", 1)
    else:
        if not allow_empty_release:
            raise ValueError("Missing release in '%s'" % evr)
        version, release = (vr, "")

    result = {
        "epoch": epoch,
        "version": version,
        "release": release,
    }

    return result


def make_nvr(nvrea_dict, add_epoch=False):
    """Make [E:]N-V-R from a nvrea dictionary.

    @param nvrea_dict: {name, version, release, epoch}
    @type nvrea_dict: dict
    @param add_epoch: add epoch to the result
    @type add_epoch: bool
    @return: [E:]N-V-R string
    @rtype str
    """

    if add_epoch:
        epoch = nvrea_dict.get("epoch", "")
        if epoch != "":
            epoch = "%s:" % epoch
    else:
        epoch = ""

    return "%s%s-%s-%s" % (epoch, nvrea_dict["name"], nvrea_dict["version"], nvrea_dict["release"])


def make_nvra(nvrea_dict, add_epoch=False, add_rpm=False):
    """Make [E:]N-V-R.A[.rpm] from a nvrea dictionary.

    @param nvrea_dict: {name, version, release, epoch, arch}
    @type nvrea_dict: dict
    @param add_epoch: add epoch to the result
    @type add_epoch: bool
    @param add_rpm: append '.rpm' suffix
    @type add_rpm: bool
    @return: [E:]N-V-R.A[.rpm] string
    @rtype str
    """

    result = "%s.%s" % (make_nvr(nvrea_dict, add_epoch), nvrea_dict["arch"])
    if add_rpm:
        result += ".rpm"
    return result


def make_nvrea_list(nvrea_dict):
    """Make [N, V, R, E, A] list from a nvrea dictionary.

    @param nvrea_dict: {name, version, release, epoch, arch}
    @type nvrea_dict: dict
    @return: [name, version, release, epoch, arch]
    @rtype: str
    """
    return [ nvrea_dict[i] for i in ("name", "version", "release", "epoch", "arch") ]


def compare_nvr(nvr_dict1, nvr_dict2, ignore_epoch=False):
    """Compare two N-V-R dictionaries.

    @param nvr_dict1: {name, version, release, epoch}
    @type nvr_dict1: dict
    @param nvr_dict2: {name, version, release, epoch}
    @type nvr_dict2: dict
    @param ignore_epoch: ignore epoch during the comparison
    @type ignore_epoch: bool
    @return: nvr1 newer than nvr2: 1, same nvrs: 0, nvr1 older: -1, different names: ValueError
    @rtype: int
    """

    nvr1 = nvr_dict1.copy()
    nvr2 = nvr_dict2.copy()

    nvr1["epoch"] = nvr1.get("epoch", None)
    nvr2["epoch"] = nvr2.get("epoch", None)

    if nvr1["name"] != nvr2["name"]:
        raise ValueError("Package names doesn't match: %s, %s" % (nvr1["name"], nvr2["name"]))

    if ignore_epoch:
        nvr1["epoch"] = 0
        nvr2["epoch"] = 0

    if nvr1["epoch"] is None:
        nvr1["epoch"] = ""

    if nvr2["epoch"] is None:
        nvr2["epoch"] = ""

    return rpm.labelCompare((str(nvr1["epoch"]), str(nvr1["version"]), str(nvr1["release"])), (str(nvr2["epoch"]), str(nvr2["version"]), str(nvr2["release"])))

def get_keys_from_header(hdr):
    """Extract signing key id from a rpm header.

    @param hdr: rpm header
    @type hdr: rpm.hdr
    @return: signing key id represented as an uppercase hex string
    @rtype: str
    """

    result = []
    head_keys = []

    for field in head_header_tags:
        sigkey = get_header_field(hdr, field)
        if sigkey:
            head_keys.append(koji.get_sigpacket_key_id(sigkey).upper())

    for field in body_header_tags:
        sigkey = get_header_field(hdr, field)
        if sigkey:
            key_id = koji.get_sigpacket_key_id(sigkey).upper()
            if key_id in head_keys:
                result.append(key_id)
            else:
                raise ValueError("%s key not found in head keys: %s" % (field, key_id))

    if len(result) > 1:
        raise ValueError("More than one key found: %s" % result)

    if len(result) == 1:
        return result[0]


def get_digest_algo_from_header(hdr):
    """Read file digest algorithm from a rpm header.

    @param hdr: rpm header
    @type hdr: rpm.hdr
    @return: digest algorithm name
    @rtype: str
    """

    # RPMTAG_FILEDIGESTALGO is not defined in older rpm
    hdr_key = getattr(rpm, "RPMTAG_FILEDIGESTALGO", 5011)
    algo_id = hdr[hdr_key]

    if algo_id == [] or algo_id is None:
        # RPMTAG_FILEDIGESTALGO is empty, fall back to md5
        algo_id = 1

    if algo_id not in FILE_DIGEST_ALGO_MAP:
        raise ValueError("Unknown file digest algorithm id: %s" % algo_id)

    return FILE_DIGEST_ALGO_MAP[algo_id]


def get_file_list_from_header(hdr):
    """Read file list from a rpm header.

    @param hdr: rpm header
    @type hdr: rpm.hdr
    @return: file_name: (color, checksum)
    @rtype: dict
    """

    result = {}
    fi = hdr.fiFromHeader()
    for file_obj in fi:
        name = file_obj[0]
        result[name] = (fi.FColor(), fi.MD5())
    return result
