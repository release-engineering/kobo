# -*- coding: utf-8 -*-


import base64
import cookielib
import fcntl
import hashlib
import httplib
import os
import socket
import ssl
import sys
import threading
import time
import urllib2
import xmlrpclib

import kobo.shortcuts

try:
    import kerberos
    USE_KERBEROS = True
except ImportError:
    USE_KERBEROS = False


__all__ = (
    "CookieTransport",
    "SafeCookieTransport",
    "retry_request_decorator",
    "encode_xmlrpc_chunks_iterator",
    "decode_xmlrpc_chunk",
)


CONNECTION_LOCK = threading.Lock()


class TimeoutHTTPConnection(httplib.HTTPConnection):
    def connect(self):
        httplib.HTTPConnection.connect(self)
        timeout = getattr(self, "_timeout", 0)
        if timeout:
            self.sock.settimeout(timeout)


class TimeoutHTTP(httplib.HTTP):
   _connection_class = TimeoutHTTPConnection

   def set_timeout(self, timeout):
       self._conn._timeout = timeout


class TimeoutHTTPSConnection(httplib.HTTPSConnection):
    def connect(self):
        httplib.HTTPSConnection.connect(self)
        timeout = getattr(self, "_timeout", 0)
        if timeout:
            self.sock.settimeout(timeout)


class TimeoutHTTPS(httplib.HTTPS):
   _connection_class = TimeoutHTTPSConnection

   def set_timeout(self, timeout):
       self._conn._timeout = timeout


class CookieResponse(object):
    """Fake response class for cookie extraction."""

    __slots__ = (
        "headers",
    )

    def __init__(self, headers):
        self.headers = headers

    def info(self):
        """Pass response headers to cookie jar."""
        return self.headers


class CookieTransport(xmlrpclib.Transport):
    """
    Cookie enabled XML-RPC transport.

    USAGE:
    >>> import xmlrpclib
        import kobo.xmlrpc
        client = xmlrpclib.ServerProxy("http://<server>/xmlrpc", transport=kobo.xmlrpc.CookieTransport())
        # for https:// connections use kobo.xmlrpc.SafeCookieTransport() instead.
    """

    _use_datetime = False # fix for python 2.5+
    scheme = "http"

    def __init__(self, *args, **kwargs):
        cookiejar = kwargs.pop("cookiejar", None)
        self.timeout = kwargs.pop("timeout", 0)

        self.proxy = kwargs.pop("proxy", None)
        if self.proxy is None:
            self.proxy = os.environ.get("http_proxy", None)
        self.realhost = None

        if hasattr(xmlrpclib.Transport, "__init__"):
            xmlrpclib.Transport.__init__(self, *args, **kwargs)

        self.cookiejar = cookiejar or cookielib.CookieJar()

        if hasattr(self.cookiejar, "load"):
            if not os.path.exists(self.cookiejar.filename):
                if hasattr(self.cookiejar, "save"):
                    self.cookiejar.save(self.cookiejar.filename)
            self.cookiejar.load(self.cookiejar.filename)

    def make_connection(self, host):
        if self.proxy:
            self.realhost = host
            host = self.proxy

        if sys.version_info[:2] < (2, 7):
            host, extra_headers, x509 = self.get_host_info(host)
            conn = TimeoutHTTP(host)
            conn.set_timeout(self.timeout)
            return conn
        else:
            CONNECTION_LOCK.acquire()
            self._connection = (None, None) # this disables connection caching which causes a race condition when running in threads
            conn = xmlrpclib.Transport.make_connection(self, host)
            CONNECTION_LOCK.release()
            if self.timeout:
                conn.timeout = self.timeout
            return conn

    def send_request(self, connection, handler, request_body):
        if self.realhost:
            handler = "%s://%s%s" % (self.scheme, self.realhost, handler) 
        return xmlrpclib.Transport.send_request(self, connection, handler, request_body)

    def send_host(self, connection, host):
        if self.realhost:
            host = self.realhost
        return xmlrpclib.Transport.send_host(self, connection, host)

    def send_cookies(self, connection, cookie_request):
        """Add cookies to the header."""
        self.cookiejar.add_cookie_header(cookie_request)

        for header, value in cookie_request.header_items():
            if header.startswith("Cookie"):
                connection.putheader(header, value)

    def _save_cookies(self, headers, cookie_request):
        cookie_response = CookieResponse(headers)
        self.cookiejar.extract_cookies(cookie_response, cookie_request)
        if hasattr(self.cookiejar, "save"):
            self.cookiejar.save(self.cookiejar.filename)

    def _kerberos_client_request(self, host, handler, errcode, errmsg, headers):
        """Kerberos auth - create a client request string"""

        # check if "Negotiate" challenge is present in headers
        negotiate = [i.lower() for i in headers.get("WWW-Authenticate", "").split(", ")]
        if "negotiate" not in negotiate:
            # negotiate not supported, raise 401 error
            raise xmlrpclib.ProtocolError(host + handler, errcode, errmsg, headers)

        # initialize GSSAPI
        service = "HTTP@%s" % host
        rc, vc = kerberos.authGSSClientInit(service)
        if rc != 1:
            errmsg = "KERBEROS: Could not initialize GSSAPI"
            raise xmlrpclib.ProtocolError(host + handler, errcode, errmsg, headers)

        # do a client step
        rc = kerberos.authGSSClientStep(vc, "")
        if rc != 0:
            errmsg = "KERBEROS: Client step failed"
            raise xmlrpclib.ProtocolError(host + handler, errcode, errmsg, headers)

        return vc, kerberos.authGSSClientResponse(vc)

    def _kerberos_verify_response(self, vc, host, handler, errcode, errmsg, headers):
        """Kerberos auth - verify client identity"""
        # verify that headers contain WWW-Authenticate header
        auth_header = headers.get("WWW-Authenticate", None)
        if auth_header is None:
            errcode = 401
            errmsg = "KERBEROS: No WWW-Authenticate header in second HTTP response"
            raise xmlrpclib.ProtocolError(host + handler, errcode, errmsg, headers)

        # verify that WWW-Authenticate contains Negotiate
        splits = auth_header.split(" ", 1)
        if (len(splits) != 2) or (splits[0].lower() != "negotiate"):
            errcode = 401
            errmsg = "KERBEROS: Incorrect WWW-Authenticate header in second HTTP response: %s" % auth_header
            raise xmlrpclib.ProtocolError(host + handler, errcode, errmsg, headers)

        # do another client step to verify response from server
        errmsg = "KERBEROS: Could not verify server WWW-Authenticate header in second HTTP response"
        try:
            rc = kerberos.authGSSClientStep(vc, splits[1])
            if rc == -1:
                errcode = 401
                raise xmlrpclib.ProtocolError(host + handler, errcode, errmsg, headers)
        except kerberos.GSSError, ex:
            errcode = 401
            errmsg += ": %s/%s" % (ex[0][0], ex[1][0])
            raise xmlrpclib.ProtocolError(host + handler, errcode, errmsg, headers)

        # cleanup
        rc = kerberos.authGSSClientClean(vc)
        if rc != 1:
            errcode = 401
            errmsg = "KERBEROS: Could not clean-up GSSAPI: %s/%s" % (ex[0][0], ex[1][0])
            raise xmlrpclib.ProtocolError(host + handler, errcode, errmsg, headers)

    def _request(self, host, handler, request_body, verbose=0):
        """Send a HTTP request."""
        h = self.make_connection(host)
        self.verbose = verbose
        if verbose:
            h.set_debuglevel(1)

        request_url = "%s://%s/" % (self.scheme, host)
        cookie_request = urllib2.Request(request_url)

        self.send_request(h, handler, request_body)
        self.send_host(h, host)
        self.send_cookies(h, cookie_request)
        self.send_user_agent(h)
        self.send_content(h, request_body)
        errcode, errmsg, headers = h.getreply()

        if errcode == 401 and USE_KERBEROS:
            vc, challenge = self._kerberos_client_request(host, handler, errcode, errmsg, headers)
            # retry the original request & add the Authorization header:
            self.send_request(h, handler, request_body)
            self.send_host(h, host)
            h.putheader("Authorization", "Negotiate %s" % challenge)
            self.send_cookies(h, cookie_request)
            self.send_user_agent(h)
            self.send_content(h, request_body)
            errcode, errmsg, headers = h.getreply()
            self._kerberos_verify_response(vc, host, handler, errcode, errmsg, headers)

        elif errcode != 200:
            raise xmlrpclib.ProtocolError(host + handler, errcode, errmsg, headers)

        self._save_cookies(headers, cookie_request)

        try:
            sock = h._conn.sock
        except AttributeError:
            sock = None

        return self._parse_response(h.getfile(), sock)

    def _single_request(self, host, handler, request_body, verbose=0):
        # issue XML-RPC request

        request_url = "%s://%s/" % (self.scheme, host)
        cookie_request = urllib2.Request(request_url)

        h = self.make_connection(host)
        self.verbose = verbose
        if verbose:
            h.set_debuglevel(1)

        try:
            self.send_request(h, handler, request_body)
            self.send_host(h, host)
            self.send_cookies(h, cookie_request)
            self.send_user_agent(h)
            self.send_content(h, request_body)

            response = h.getresponse(buffering=True)

            if response.status == 401 and USE_KERBEROS:
                vc, challenge = self._kerberos_client_request(host, handler, response.status, response.reason, response.msg)

                # discard any response data
                if (response.getheader("content-length", 0)):
                    response.read()

                # retry the original request & add the Authorization header:
                self.send_request(h, handler, request_body)
                self._extra_headers = [("Authorization", "Negotiate %s" % challenge)]
                self.send_host(h, host)
                self.send_user_agent(h)
                self.send_content(h, request_body)
                self._extra_headers = []
                response = h.getresponse(buffering=True)
                self._kerberos_verify_response(vc, host, handler, response.status, response.reason, response.msg)

            if response.status == 200:
                self.verbose = verbose
                self._save_cookies(response.msg, cookie_request)
                return self.parse_response(response)
        except xmlrpclib.Fault:
            raise
        except Exception:
            # All unexpected errors leave connection in
            # a strange state, so we clear it.
            self.close()
            raise

        # discard any response data and raise exception
        if (response.getheader("content-length", 0)):
            response.read()
        raise xmlrpclib.ProtocolError(host + handler, response.status, response.reason, response.msg)

    # override the appropriate request method
    if hasattr(xmlrpclib.Transport, "single_request"):
        # python 2.7+
        single_request = _single_request
    else:
        # python 2.6-
        request = _request


class SafeCookieTransport(xmlrpclib.SafeTransport, CookieTransport):
    """
    Cookie enabled XML-RPC transport over HTTPS.

    USAGE: see CookieTransport
    """
    scheme = "https"

    def make_connection(self, host):
        if self.proxy:
            # Connect to proxy and send CONNECT command
            connection = CookieTransport.make_connection(self, host) # sets self.realhost
            request = "CONNECT %s HTTP/1.0\r\n\r\n" % self.realhost
            connection.send(request)

            # Get proxy response
            response = connection.response_class(connection.sock, strict=connection.strict, method=connection._method)
            version, code, message = response._read_status()

            if code != 200:
                self.close()
                raise socket.error("Tunnel connection failed: %d %s" % (code, message.strip()))

            while True:
                line = response.fp.readline()
                if line == '\r\n': 
                    break

            connection.sock = ssl.wrap_socket(connection.sock, None, None)
            return connection

        if sys.version_info[:2] < (2, 7):
            host, extra_headers, x509 = self.get_host_info(host)
            conn = TimeoutHTTPS(host, None, **(x509 or {}))
            conn.set_timeout(self.timeout)
            return conn
        else:
            conn = xmlrpclib.SafeTransport.make_connection(self, host)
            if self.timeout:
                conn.timeout = self.timeout
            return conn

    # override the appropriate request method
    if hasattr(xmlrpclib.Transport, "single_request"):
        # python 2.7+
        single_request = CookieTransport._single_request
    else:
        # python 2.6-
        request = CookieTransport._request

    def __init__(self, *args, **kwargs):
        CookieTransport.__init__(self, *args, **kwargs)

    def send_request(self, connection, handler, request_body):
        if self.realhost:
            handler = "%s://%s%s" % (self.scheme, self.realhost, handler) 
        return xmlrpclib.SafeTransport.send_request(self, connection, handler, request_body)

    def send_host(self, connection, host):
        if self.realhost:
            host = self.realhost
        return xmlrpclib.SafeTransport.send_host(self, connection, host)


def retry_request_decorator(transport_class):
    """Use this class decorator on a Transport to retry requests which failed on socket errors."""
    class RetryTransportClass(transport_class):
        def __init__(self, *args, **kwargs):
            self.retry_count = kwargs.pop("retry_count", 5)
            self.retry_timeout = kwargs.pop("retry_timeout", 30)
            if hasattr(transport_class, "__init__"):
                transport_class.__init__(self, *args, **kwargs)

        def request(self, *args, **kwargs):
            if self.retry_count == 0:
                return transport_class.request(self, *args, **kwargs)

            for i in xrange(self.retry_count + 1):
                try:
                    result = transport_class.request(self, *args, **kwargs)
                    return result
                except KeyboardInterrupt:
                    raise
                except (socket.error, socket.herror, socket.gaierror, socket.timeout), ex:
                    if i >= self.retry_count:
                        raise
                    retries_left = self.retry_count - i
                    retries = "%d %s left" % (retries_left, retries_left == 1 and "retry" or "retries") # 1 retry left / X retries left
                    print >> sys.stderr, "XML-RPC connection to %s failed: %s, %s" % (args[0], " ".join(ex.args[1:]), retries)
                    time.sleep(self.retry_timeout)

    RetryTransportClass.__name__ = transport_class.__name__
    RetryTransportClass.__doc__ = transport_class.__name__
    return RetryTransportClass


def encode_xmlrpc_chunks_iterator(file_obj):
    """
    Prepare data for a xml-rpc transfer.
    Iterate through (chunk_start, chunk_len, chunk_checksum, encoded_chunk) tuples.
    Final tuple is (total_length, -1, total_checksum, "").

    @param file_obj: file object (or StringIO, etc.)
    @type  file_obj: file
    @return: (chunk_start, chunk_len, chunk_checksum, encoded_chunk)
    @rtype:  (str, str, str, str)
    """

    CHUNK_SIZE = 1024 ** 2
    checksum = hashlib.sha256()
    chunk_start = file_obj.tell()

    while True:
        chunk = file_obj.read(CHUNK_SIZE)
        if not chunk:
            break
        checksum.update(chunk)
        encoded_chunk = base64.encodestring(chunk)
        yield (str(chunk_start), str(len(chunk)), hashlib.sha256(chunk).hexdigest().lower(), encoded_chunk)
        chunk_start += len(chunk)

    yield (str(chunk_start), -1, checksum.hexdigest().lower(), "")


def decode_xmlrpc_chunk(chunk_start, chunk_len, chunk_checksum, encoded_chunk, write_to=None, mode=0644):
    """
    Decode a data chunk and optionally write it to a file.

    @param chunk_start: chunk start position in the file (-1 for append)
    @type  chunk_start: str
    @param chunk_len: chunk length
    @type  chunk_len: str
    @param chunk_checksum: sha256 checksum (lower case)
    @type  chunk_checksum: str
    @param encoded_chunk: base64 encoded chunk
    @type  encoded_chunk: str
    @param write_to: path to a file in which the decoded data will be written
    @type  write_to: str
    @param mode: file permissions (example: 0644)
    @type  mode: int
    @return: decoded data
    @rtype:  str
    """

    chunk_start = int(chunk_start)
    chunk_len = int(chunk_len)
    chunk = base64.decodestring(encoded_chunk)

    if chunk_len not in (-1, len(chunk)):
        raise ValueError("Chunk length doesn't match.")

    if chunk_len == -1:
        chunk = ""
    elif chunk_checksum != hashlib.sha256(chunk).hexdigest().lower():
        raise ValueError("Chunk checksum doesn't match.")

    if not write_to:
        return chunk

    # code below handles writing to a file

    target_dir = os.path.dirname(write_to)
    if not os.path.isdir(target_dir):
        try:
            os.makedirs(target_dir, mode=0755)
        except OSError, ex:
            if ex.errno != 17:
                raise

    fd = os.open(write_to, os.O_RDWR | os.O_CREAT, mode)
    fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        if chunk_start != -1:
            os.ftruncate(fd, chunk_start)
        os.lseek(fd, 0, 2) # 2=os.SEEK_END
        os.write(fd, chunk)
    finally:
        fcntl.lockf(fd, fcntl.LOCK_UN)
        os.close(fd)

    if chunk_start != -1 and chunk_len == -1:
        # final chunk, compute checksum of whole file
        file_checksum = kobo.shortcuts.compute_file_checksums(write_to, ["sha256"])["sha256"]
        if file_checksum != chunk_checksum:
            raise ValueError("File checksum does not match.")

    return chunk
