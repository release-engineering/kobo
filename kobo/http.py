# -*- coding: utf-8 -*-


# based on: http://code.activestate.com/recipes/146306/


import httplib
import mimetypes
import os

from kobo.shortcuts import random_string


class POSTTransport(object):
    __slots__ = (
        "_variables",
        "_files",
        "_boundary",
        "last_response",
    )

    def __init__(self):
        self._variables = []
        self._files = []
        self._boundary = random_string(32)
        self.last_response = None


    def get_content_type(self, file_name):
        return mimetypes.guess_type(file_name)[0] or "application/octet-stream"


    def add_variable(self, key, value):
        self._variables.append((str(key), str(value)))


    def add_file(self, key, file_name):
        if type(file_name) is not str:
            raise TypeError("Invalid type of 'file_name': %s" % type(file_name))

        if not os.path.isfile(file_name):
            raise OSError("Not a file: %s" % file_name)

        self._files.append((str(key), str(file_name)))


    def flush_data(self):
        self._variables = []
        self._files = []


    def send_to_host(self, host, selector, port=None, secure=False, flush=True):
        data = []
        for key, value in self._variables:
            data.extend((
                "--%s" % self._boundary, 
                'Content-Disposition: form-data; name="%s"' % key,
                "",
                value,
            ))

        for key, file_name in self._files:
            fo = open(file_name, "rb")
            file_data = fo.read()
            fo.close()

            data.extend((
                "--%s" % self._boundary,
                'Content-Disposition: form-data; name="%s"; filename="%s"' % (key, os.path.basename(file_name)),
                "Content-Type: %s" % self.get_content_type(file_name),
                "",
                file_data,
            ))

        if not data:
            return None

        data.extend(("--%s--" % self._boundary,""))
        content = "\r\n".join(data)
        content_type = "multipart/form-data; boundary=" + self._boundary

        if secure:
            request = httplib.HTTPSConnection(host, port)
        else:
            request = httplib.HTTPConnection(host, port)
        
        request.putrequest("POST", selector)
        request.putheader("content-type", content_type)
        request.putheader("content-length", str(len(content)))
        request.endheaders()
        request.send(content)
        response = request.getresponse()

        if flush: 
            self.flush_data()

        return response.status, response.read()
