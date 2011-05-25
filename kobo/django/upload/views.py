# -*- coding: utf-8 -*-


import hashlib
import tempfile
import shutil
import os
import datetime

from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseForbidden, HttpResponseServerError
from django.views.decorators.csrf import csrf_exempt
from kobo.decorators import well_behaved

from models import UPLOAD_STATES, FileUpload


@well_behaved
def catch_exceptions(old_view):
    """Catch exceptions in a view and return ServerError with exception text."""
    def new_view(*args, **kwargs):
        try:
            return old_view(*args, **kwargs)
        except Exception, ex:
            return HttpResponseServerError(str(ex))
    return new_view


@csrf_exempt
@catch_exceptions
def file_upload(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    upload_id = request.POST.get("upload_id")
    upload_key = request.POST.get("upload_key")
    fu = request.FILES["file"]

    try:
        upload = FileUpload.objects.get(id=upload_id, upload_key=upload_key)
    except:
        return HttpResponseForbidden("Not allowed to upload the file.")

    upload_path = os.path.join(upload.target_dir, upload.name)

    if os.path.isfile(upload_path):
        upload.state = UPLOAD_STATES["FAILED"]
        upload.save()
        # remove file
        return HttpResponseServerError("File already exists.")

    # TODO: check size
    # TODO: check target_dir? create it?
    # don't re-upload FINISHED or STARTED

    tmp_dir = tempfile.mkdtemp()
    tmp_file_name = os.path.join(tmp_dir, upload.name)
    tmp_file = open(tmp_file_name, "wb")
    sum = hashlib.sha256()

    # transaction, commit save()
    upload.state = UPLOAD_STATES["STARTED"]
    upload.save()

    for chunk in fu.chunks():
        tmp_file.write(chunk)
        sum.update(chunk)
    tmp_file.close()

    checksum = sum.hexdigest().lower()

    if checksum != upload.checksum.lower():
        upload.state = UPLOAD_STATES["FAILED"]
        upload.save()
        # remove file
        return HttpResponseServerError("Checksum mismatch.")

    if not os.path.isdir(upload.target_dir):
        os.makedirs(upload.target_dir)

    shutil.move(tmp_file_name, upload.target_dir)
    shutil.rmtree(tmp_dir)

    upload.state = UPLOAD_STATES["FINISHED"]
    upload.dt_finished = datetime.datetime.now()
    upload.save()

    # upload.save can modify state if there is a race
    if upload.state == UPLOAD_STATES['FAILED']:
        return HttpResponseServerError("Checksum mismatch.")

    return HttpResponse("Upload finished.")
