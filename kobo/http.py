# -*- coding: utf-8 -*-


# based on: http://code.activestate.com/recipes/146306/


import httplib
import mimetypes
import os

from kobo.shortcuts import random_string


class POSTTransport(object):
    """
    POST transport.

    USAGE:
    >>> import kobo.http
        t = kobo.http.POSTTransport()
        t.add_variable("foo", "bar")
        t.add_file("foofile", "/tmp/some_file")
        t.send_to_host("somehost", "/cgi-bin/upload")
    """

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
        """Guess the mime type of a file.

        @param file_name: file name
        @type file_name: str
        @return: MIME type
        @rtype: str
        """
        return mimetypes.guess_type(file_name)[0] or "application/octet-stream"

    def add_variable(self, key, value):
        """Add a variable to the POST request."""
        self._variables.append((str(key), str(value)))

    def add_file(self, key, file_name):
        """
        Add a file to the POST request.

        @param key: key
        @type key: str
        @param file_name: file name
        @type file_name: str
        """
        if type(file_name) is not str:
            raise TypeError("Invalid type of 'file_name': %s" % type(file_name))

        if not os.path.isfile(file_name):
            raise OSError("Not a file: %s" % file_name)

        self._files.append((str(key), str(file_name)))

    def flush_data(self):
        """Flush variables and files from the request."""
        self._variables = []
        self._files = []

    def send_to_host(self, host, selector, port=None, secure=False, flush=True):
        """
        Send the POST request to a host.

        @param host: host address
        @type host: str
        @param selector: selector/path string
        @type selector: str
        @param port: port number
        @type port: int
        @param secure: use https
        @type secure: bool
        @param flush: flush data after send
        @type flush: bool
        @return: (response status code, response data body)
        @rtype: (int, str)
        """
        content_length = 0

        variables = []
        for key, value in self._variables:
            variables.extend((
                "--%s" % self._boundary,
                'Content-Disposition: form-data; name="%s"' % key,
                "",
                value,
            ))
        variables_data = "\r\n".join(variables)
        content_length += len(variables_data)
        content_length += 2 # '\r\n'

        files = []
        for key, file_name in self._files:
            file_data = "\r\n".join((
                "--%s" % self._boundary,
                'Content-Disposition: form-data; name="%s"; filename="%s"' % (key, os.path.basename(file_name)),
                "Content-Type: %s" % self.get_content_type(file_name),
                "",
                "", # this adds extra newline before file data
            ))
            files.append((file_name, file_data))
            content_length += len(file_data)
            content_length += os.path.getsize(file_name)
            content_length += 2 # '\r\n'

        footer_data = "\r\n".join(("--%s--" % self._boundary, ""))
        content_length += len(footer_data)
        content_type = "multipart/form-data; boundary=" + self._boundary

        if secure:
            request = httplib.HTTPSConnection(host, port)
        else:
            request = httplib.HTTPConnection(host, port)

        request.putrequest("POST", selector)
        request.putheader("content-type", content_type)
        request.putheader("content-length", str(content_length))
        request.endheaders()
        request.send(variables_data)
        request.send("\r\n")
        for file_name, file_data in files:
            request.send(file_data)
            file_obj = open(file_name, "r")
            while 1:
                chunk = file_obj.read(1024**2)
                if not chunk:
                    break
                request.send(chunk)
            request.send("\r\n")

        request.send(footer_data)
        response = request.getresponse()

        if flush:
            self.flush_data()

        return response.status, response.read()
