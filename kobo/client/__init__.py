# -*- coding: utf-8 -*-


# TODO: login using SSL certificate (like in koji)


import os
import base64
import hashlib
import urlparse
import xmlrpclib

import kobo.conf
from kobo.cli import *
from kobo.exceptions import ImproperlyConfigured
from kobo.xmlrpc import CookieTransport, SafeCookieTransport, retry_request_decorator
from kobo.http import POSTTransport


__all__ = (
    "CommandContainer",
    "CommandOptionParser",
    "ClientCommand",
    "HubProxy",
    "Option",
)


class ClientCommand(Command):
    __slots__ = (
        "hub",
        "hub_proxy_class",
        "conf_environ_key",
    )

    enabled = False
    hub_proxy_class = None
    conf_environ_key = None


    def set_hub(self, username=None, password=None):
        HubProxyClass = self.hub_proxy_class or HubProxy

        conf = kobo.conf.PyConfigParser()
        if self.conf_environ_key is not None:
            conf.load_from_file(os.environ[self.conf_environ_key])

        if hasattr(kobo.conf, "settings"):
            conf.load_from_conf(kobo.conf.settings)

        if username:
            if password is None:
                password = self.password_prompt(default_value=password)
            conf["AUTH_METHOD"] = "password"
            conf["USERNAME"] = username
            conf["PASSWORD"] = password

        self.hub = HubProxyClass(conf=conf)


    def write_task_id_file(self, task_id, filename=None, append=False):
        if filename is not None:
            if append:
                f = open(filename, "a+")
            else:
                f = open(filename, "w")
            f.write("%s\n" % task_id)
            f.close()


class HubProxy(object):
    """A Hub client (thin ServerProxy wrapper)."""

    __slots__ = (
        "_conf",
        "_conf_environ_key",
        "_client_type",
        "_hub",
        "_hub_url",
        "_auth_method",
        "_transport",
        "_auto_logout",
        "_logger",
        "_logged_in",
    )


    def __init__(self, client_type=None, logger=None, transport=None, auto_logout=True, conf=None, **kwargs):
        self._conf = kobo.conf.PyConfigParser()
        self._hub = None

        # load default config
        default_config = os.path.abspath(os.path.join(os.path.dirname(__file__), "default.conf"))
        self._conf.load_from_file(default_config)

        # update data from config specified in os.environ
        if hasattr(self, "_conf_environ_key") and os.environ.get(self._conf_environ_key, None):
            self._conf.load_from_file(os.environ[self._conf_environ_key])

        # update data from another config
        if conf is not None:
            self._conf.load_from_conf(conf)

        # update data from kwargs
        self._conf.load_from_dict(kwargs)

        # initialize properties
        self._client_type   = client_type or "client"
        self._hub_url       = self._conf["HUB_URL"]
        self._auth_method   = self._conf["AUTH_METHOD"]
        self._auto_logout   = auto_logout
        self._logger        = logger
        self._logged_in     = False

        if transport is not None:
            self._transport = transport
        elif self._hub_url.startswith("https://"):
            self._transport = retry_request_decorator(SafeCookieTransport)()
        else:
            self._transport = retry_request_decorator(CookieTransport)()

        # self._hub is created here
        try:
            self._login(verbose=self._conf.get("DEBUG_XMLRPC"))
        except KeyboardInterrupt:
            raise
        except Exception, e:
            self._logger and self._logger.warn("Authentication failed")
            raise


    def __del__(self):
        if hasattr(self._transport, "retry_count"):
            self._transport.retry_count = 0
        if getattr(self, "_auto_logout", False) and self._logged_in:
            try:
                self._logout()
            except:
                pass


    def __getattr__(self, name):
        try:
            return getattr(self._hub, name)
        except:
            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, name))


    def _login(self, force=False, verbose=False):
        """Login to the hub.
        - self._hub instance is created in this method
        - session information is stored in a cookie in self._transport
        """

        login_method_name = "_login_%s" % self._auth_method
        if not hasattr(self, login_method_name):
            raise ImproperlyConfigured("Unknown authentication method: %s" % self._auth_method)

        # create new self._hub instance (only once, when calling constructor)
        if self._hub is None:
            self._hub = xmlrpclib.ServerProxy("%s/%s/" % (self._hub_url, self._client_type), allow_none=True, transport=self._transport, verbose=verbose)

        if force or self._hub.auth.renew_session():
            self._logger and self._logger.info("Creating new session...")
            try:
                # logout to delete current session information
                self._logout()
            except KeyboardInterrupt:
                raise
            except Exception, ex:
                self._logger and self._logger.error("Failed to log out: %s" % ex)

            try:
                login_method = getattr(self, login_method_name)
                login_method()
                self._logged_in = True
            except KeyboardInterrupt:
                raise
            except Exception, ex:
                self._logger and self._logger.error("Failed to create new session: %s" % ex)
                raise
            else:
                self._logger and self._logger.info("New session created.")


    def _logout(self):
        """Logout from hub"""
        if hasattr(self, "_hub"):
            self._hub.auth.logout()


    def _login_password(self):
        """Login using username and password."""
        username = self._conf["USERNAME"]
        password = self._conf["PASSWORD"]
        self._hub.auth.login_password(username, password)


    def _login_worker_key(self):
        """Login using worker key."""
        worker_key = self._conf["WORKER_KEY"]
        self._hub.auth.login_worker_key(worker_key)


    def _login_krbv(self):
        """Login using kerberos credentials (uses python-krbV)."""

        def get_server_principal(service=None, realm=None):
            """Convert hub url to kerberos principal."""
            hostname = urlparse.urlparse(self._hub_url)[1]
            # remove port from hostname
            hostname = hostname.split(":")[0]

            if realm is None:
                # guess realm: last two parts from hostname
                realm = ".".join(hostname.split(".")[-2:]).upper()
            if service is None:
                service = "HTTP"
            return '%s/%s@%s' % (service, hostname, realm)


        # read default values from settings
        principal = self._conf.get("KRB_PRINCIPAL")
        keytab = self._conf.get("KRB_KEYTAB")
        service = self._conf.get("KRB_SERVICE")
        realm = self._conf.get("KRB_REALM")
        ccache = self._conf.get("KRB_CCACHE")
        proxyuser = self._conf.get("KRB_PROXYUSER")

        import krbV
        ctx = krbV.default_context()

        if ccache is not None:
            ccache = krbV.CCache(name='FILE:' + ccache, context=ctx)
        else:
            ccache = ctx.default_ccache()

        if principal is not None:
            if keytab is not None:
                cprinc = krbV.Principal(name=principal, context=ctx)
                keytab = krbV.Keytab(name=keytab, context=ctx)
                ccache.init(cprinc)
                ccache.init_creds_keytab(principal=cprinc, keytab=keytab)
            else:
                raise ImproperlyConfigured("Cannot specify a principal without a keytab")
        else:
            # connect using existing credentials
            cprinc = ccache.principal()

        sprinc = krbV.Principal(name=get_server_principal(service=service, realm=realm), context=ctx)

        ac = krbV.AuthContext(context=ctx)
        ac.flags = krbV.KRB5_AUTH_CONTEXT_DO_SEQUENCE | krbV.KRB5_AUTH_CONTEXT_DO_TIME
        ac.rcache = ctx.default_rcache()

        # create and encode the authentication request
        (ac, req) = ctx.mk_req(server=sprinc, client=cprinc, auth_context=ac, ccache=ccache, options=krbV.AP_OPTS_MUTUAL_REQUIRED)
        req_enc = base64.encodestring(req)

        self._hub.auth.login_krbv(req_enc)


    def upload_file(self, file_name, target_dir):
        scheme, netloc, path, params, query, fragment = urlparse.urlparse("%s/upload/" % self._hub_url)
        if ":" in netloc:
            host, port = netloc.split(":", 1)
        else:
            host, port = netloc, None

        sum = hashlib.sha256()
        fo = open(file_name, "rb")
        while True:
            chunk = fo.read(1024**2)
            if not chunk:
                break
            sum.update(chunk)
        fo.close()
        checksum = sum.hexdigest().lower()
        
        fsize = os.path.getsize(file_name)
        upload_id, upload_key = self.upload.register_upload(os.path.basename(file_name), checksum, fsize, target_dir)

        secure = (scheme == "https")
        upload = POSTTransport()
        upload.add_variable("upload_id", upload_id)
        upload.add_variable("upload_key", upload_key)
        upload.add_file("file", file_name)

        err_code, err_msg = upload.send_to_host(host, path, port, secure)
        return upload_id, err_code, err_msg
