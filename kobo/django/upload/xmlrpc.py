# -*- coding: utf-8 -*-


import os

from django.conf import settings

from models import FileUpload
from kobo.django.xmlrpc.decorators import login_required


__all__ = (
    "register_upload",
    "delete_upload",
)


@login_required
def register_upload(request, name, checksum, size, target_dir):
    upload_dir = getattr(settings, "UPLOAD_DIR", None)
    if upload_dir is not None:
        target_dir = os.path.join(upload_dir, target_dir)
        if not target_dir.startswith(upload_dir):
            raise RuntimeError("Target directory (%s) is outside upload dir: %s" % (target_dir, upload_dir))

    upload = FileUpload()
    upload.owner = request.user
    upload.name = name
    upload.checksum = checksum.lower()
    upload.size = size
    upload.target_dir = target_dir
    upload.save()
    return (upload.id, upload.upload_key)

@login_required
def delete_upload(request, upload_id):
    try:
        FileUpload.objects.get(id = upload_id).delete()
        return True
    except:
        return False
