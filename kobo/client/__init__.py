# -*- coding: utf-8 -*-


# TODO: login using SSL certificate (like in koji)


"""
ClientCommandContainer HOWTO
============================
# ClientCommandContainer extends kobo.cli.CommandContainer
# by adding 'hub' attribute and 'set_hub' method.


1) Import modules
-----------------
import kobo.client
import kobo.client.commands
# Assuming all commands are in <project_name>/commands/cmd_*.py modules.
import <project_name>.commands


2) Inherit the container
------------------------
# Inherit container to make sure nobody will change plugins I registered.
class <ProjectName>CommandContainer(kobo.client.ClientCommandContainer):
    pass


2) Register plugins
-------------------
<ProjectName>CommandContainer.register_module(kobo.client.commands, prefix="cmd_")
<ProjectName>CommandContainer.register_module(<project_name>.commands, prefix="cmd_")


3) Define and call main() function
----------------------------------
def main(args=None):
    config_file = os.environ.get("<PROJECT_NAME>_CONFIG_FILE", "/etc/<project_name>.conf")
    conf = kobo.conf.PyConfigParser()
    conf.load_from_file(config_file)
    command_container = <ProjectName>CommandContainer(conf)
    parser = kobo.cli.CommandOptionParser(command_container=command_container, add_username_password_options=True)
    parser.run(args)
    sys.exit(0)


4) Create commands
------------------
# Commands should be placed in a separate module, usually <project_name>.commands.
# One command per sub-module makes things readable.

import kobo.client

class Add_User(kobo.client.ClientCommand):
    '''add a user account'''
    enabled = True
    admin = True

    def options(self):
        self.parser.usage = "%%prog %s" % self.normalized_name

    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        hub = kwargs.pop("hub", None)

        self.set_hub(username, password, hub)
        # self.hub.client.add_user(...)
"""


import os
import base64
import hashlib
import ssl
import warnings
import six.moves.urllib.parse as urlparse
from six.moves import xmlrpc_client as xmlrpclib

import kobo.conf
import kobo.cli
import kobo.http
import kobo.xmlrpc
from kobo.exceptions import AuthenticationError, ImproperlyConfigured


__all__ = (
    "BaseClientCommandContainer",
    "CommandContainer",
    "CommandOptionParser",
    "ClientCommand",
    "ClientCommandContainer",
    "HubProxy",
    "Option",
)


class BaseClientCommandContainer(kobo.cli.CommandContainer):
    """A basic CommandContainer class that implements methods needed for CommandOptionParser"""
    def __init__(self):
        self.conf = kobo.conf.PyConfigParser()

    def set_hub(self, username=None, password=None, hub=None):
        if username:
            if password is None:
                password = kobo.cli.password_prompt(default_value=password)
            self.conf["AUTH_METHOD"] = "password"
            self.conf["USERNAME"] = username
            self.conf["PASSWORD"] = password

        if hub:
            self.conf["HUB_URL"] = hub

        self.hub = HubProxy(conf=self.conf)


class ClientCommandContainer(BaseClientCommandContainer):
    """A general-purpose subclass of BaseClientCommandContainer that loads configurations immediately at instantiation"""
    def __init__(self, conf, **kwargs):
        super(ClientCommandContainer, self).__init__()
        self.conf.load_from_conf(conf)
        self.conf.load_from_dict(kwargs)


class ClientCommand(kobo.cli.Command):
    pass


class HubProxy(object):
    """A Hub client (thin ServerProxy wrapper)."""

    def __init__(self, conf, client_type=None, logger=None, transport=None, auto_logout=None, **kwargs):
        self._conf = kobo.conf.PyConfigParser()
        self._hub = None

        # load default config
        default_config = os.path.abspath(os.path.join(os.path.dirname(__file__), "default.conf"))
        self._conf.load_from_file(default_config)

        # update config with another one
        if conf is not None:
            self._conf.load_from_conf(conf)

        # update config with kwargs
        self._conf.load_from_dict(kwargs)

        # initialize properties
        self._client_type = client_type or "client"
        self._hub_url = self._conf["HUB_URL"]
        self._auth_method = self._conf["AUTH_METHOD"]
        self._logger = logger
        self._logged_in = False

        if auto_logout is not None:
            warnings.warn("auto_logout is deprecated and has no effect", DeprecationWarning)

        if transport is not None:
            self._transport = transport
        else:
            transport_args = {}
            if self._hub_url.startswith("https://"):
                TransportClass = kobo.xmlrpc.retry_request_decorator(kobo.xmlrpc.SafeCookieTransport)
                if hasattr(ssl, 'create_default_context'):
                    ssl_context = ssl.create_default_context()
                    if self._conf.get('CA_CERT'):
                        ssl_context.load_verify_locations(cafile=self._conf['CA_CERT'])
                    else:
                        ssl_context.check_hostname = False
                        ssl_context.verify_mode = ssl.CERT_NONE
                    transport_args['context'] = ssl_context
            else:
                TransportClass = kobo.xmlrpc.retry_request_decorator(kobo.xmlrpc.CookieTransport)
            self._transport = TransportClass(**transport_args)

        # self._hub is created here
        try:
            self._login(verbose=self._conf.get("DEBUG_XMLRPC"))
        except KeyboardInterrupt:
            raise
        except Exception as ex:
            self._logger and self._logger.warn("Authentication failed")
            raise

    def __getattr__(self, name):
        try:
            return getattr(self._hub, name)
        except:
            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, name))

    def check_hub_connectivity(self, hub, timeout=5):
        """
        Check the connectivity of an XML-RPC endpoint.

        Returns:
            A tuple containing a boolean indicating the connectivity status
            and error message if the connectivity check fails.

        """
        import requests
        try:
            response = requests.get(hub, timeout=timeout)

            # A valid xmlrpc endpoint may yield 404 when accessing via http, we need to check
            # whether the response is of the desired content type
            if response.content:
                content_type = response.headers.get("Content-Type")
                if content_type and ("html" in content_type or "xml" in content_type):
                    # If the content type contains html/xml, the endpoint might be valid
                    return (True, None)
                else:
                    return (False, "The response does not indicate the expected HTML/XML content type.")
            else:
                # If the response is empty, the endpoint is likely invalid
                return (False, "The response has no content.")
        except Exception as e:
            return (False, f"Error: {e}")

    @property
    def is_logged_in(self):
        return self._logged_in

    def login(self):
        """Login to the hub.
        
        If the hub is already logged in this method does not reattempt it.

        Raises:
            AuthenticationError when login fails.
        """
        if not self.is_logged_in:
            self._login(force=True)
            if not self.is_logged_in:
                raise AuthenticationError("Login attempt failed.")

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
            success, message = self.check_hub_connectivity(self._hub_url)
            if success:
                self._hub = xmlrpclib.ServerProxy("%s/%s/" % (self._hub_url, self._client_type), allow_none=True, transport=self._transport, verbose=verbose)
            else:
                self._logger and self._logger.error(f"Failed to connect to {self._hub_url}: {message}")
                raise ValueError(f"Failed to connect to {self._hub_url}: {message}")

        if force or self._hub.auth.renew_session():
            self._logger and self._logger.info("Creating new session...")
            try:
                # logout to delete current session information
                self._logout()
            except KeyboardInterrupt:
                raise
            except Exception as ex:
                self._logger and self._logger.error("Failed to log out: %s" % ex)

            try:
                login_method = getattr(self, login_method_name)
                login_method()
                self._logged_in = True
            except KeyboardInterrupt:
                raise
            except Exception as ex:
                self._logger and self._logger.debug("Failed to create new session: %s" % ex)
            else:
                self._logger and self._logger.info("New session created.")

    def _logout(self):
        """Logout from hub"""
        if hasattr(self, "_hub"):
            self._hub.auth.logout()

    def _login_password(self):
        """Login using username and password."""
        username = self._conf.get("USERNAME")
        password = self._conf.get("PASSWORD")
        if not username:
            raise AuthenticationError("USERNAME is not set")
        self._hub.auth.login_password(username, password)

    def _login_worker_key(self):
        """Login using worker key."""
        worker_key = self._conf.get("WORKER_KEY")
        if not worker_key:
            raise AuthenticationError("WORKER_KEY is not set")
        self._hub.auth.login_worker_key(worker_key)

    def _login_krbv(self):
        """Login using kerberos credentials (uses python-krbV)."""

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

        sprinc = krbV.Principal(name=self.get_server_principal(service=service, realm=realm), context=ctx)

        ac = krbV.AuthContext(context=ctx)
        ac.flags = krbV.KRB5_AUTH_CONTEXT_DO_SEQUENCE | krbV.KRB5_AUTH_CONTEXT_DO_TIME
        ac.rcache = ctx.default_rcache()

        # create and encode the authentication request
        try:
            ac, req = ctx.mk_req(server=sprinc, client=cprinc, auth_context=ac, ccache=ccache, options=krbV.AP_OPTS_MUTUAL_REQUIRED)
        except krbV.Krb5Error as ex:
            if getattr(ex, "err_code", None) == -1765328377:
                ex.message += ". Make sure you correctly set KRB_REALM (current value: %s)." % realm
                ex.args = (ex.err_code, ex.message)
            raise ex
        encode_func = base64.encodebytes if hasattr(base64, "encodebytes") else base64.encodestring
        req_enc = encode_func(req)

        self._hub.auth.login_krbv(req_enc)
    
    def _login_token_oidc(self):
        """Login using OIDC endpoint (with Client Credentials Flow - using tokens)"""
        login_url = urlparse.urljoin(self._hub_url, "auth/tokenoidclogin/")
        client_id = self._conf.get("OIDC_CLIENT_ID")
        client_secret = self._conf.get("OIDC_CLIENT_SECRET")
        auth_server_token_url = self._conf.get("OIDC_AUTH_SERVER_TOKEN_URL")
        request_args = {}

        import requests

        token_data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "openid"
        }
        token_response = requests.post(auth_server_token_url, data=token_data, timeout=30)
        token_response.raise_for_status()
        headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}

        # NOTE behavior difference from hub proxy overall:
        # HubProxy by default DOES NOT verify https connections :(
        # See the constructor. It could be repeated here by defaulting verify to False,
        # but let's not do that, instead you must have an unbroken SSL setup to
        # use this auth method.
        if self._conf.get("CA_CERT"):
            request_args["verify"] = self._conf["CA_CERT"]

        with requests.Session() as s:
            s.cookies = self._transport.cookiejar
            response = s.get(
                login_url,
                headers=headers,
                **request_args
            )
        
        self._logger and self._logger.debug(
            "Login response: %s %s", response, response.headers
        )
        response.raise_for_status()


    def _login_gssapi(self):
        """Login using kerberos credentials (uses gssapi)."""

        login_url = urlparse.urljoin(self._hub_url, "auth/krb5login/")
        return self._login_gssapi_common(login_url, force_service=True, allow_redirects=False)
    
    def _login_oidc(self):
        """Login using oidc endpoint (with gssapi)."""
        login_url = urlparse.urljoin(self._hub_url, "auth/oidclogin/")
        return self._login_gssapi_common(login_url, force_service=False, allow_redirects=True)

    def _login_gssapi_common(self, login_url, force_service, allow_redirects):
        """Common authentication logic for auth methods using gssapi.
        - if force_service is True, client always calculates a service principal up-front
          even if no KRB_SERVICE was set in config. Breaks OIDC since we are not actually
          doing gssapi with the kobo hub.
        - if allow_redirects is True, authentication is allowed to follow redirects. Required
          in the OIDC case.
        """

        # read default values from settings
        principal = self._conf.get("KRB_PRINCIPAL")
        keytab = self._conf.get("KRB_KEYTAB")
        service = self._conf.get("KRB_SERVICE")
        realm = self._conf.get("KRB_REALM")
        ccache = self._conf.get("KRB_CCACHE")

        import requests
        import gssapi
        import requests_gssapi

        request_args = {}

        # NOTE behavior difference from hub proxy overall:
        # HubProxy by default DOES NOT verify https connections :(
        # See the constructor. It could be repeated here by defaulting verify to False,
        # but let's not do that, instead you must have an unbroken SSL setup to
        # use this auth method.
        if self._conf.get("CA_CERT"):
            request_args["verify"] = self._conf["CA_CERT"]

        auth_args = {"mutual_authentication": requests_gssapi.OPTIONAL}

        if service or force_service:
            if realm is None:
                # let gssapi select the correct realm (according to system configuration)
                if service is None:
                    service = "HTTP"
                server_name = '%s@%s' % (service, self.get_hub_hostname()) 
                server_name = gssapi.Name(server_name, gssapi.NameType.hostbased_service)
            else:
                server_name = self.get_server_principal(service=service, realm=realm)
                server_name = gssapi.Name(server_name, gssapi.NameType.kerberos_principal)
            auth_args["target_name"] = server_name

        if principal is not None:
            if keytab is None:
                raise ImproperlyConfigured(
                    "Cannot specify a principal without a keytab"
                )
            name = gssapi.Name(principal, gssapi.NameType.kerberos_principal)
            store = {"client_keytab": keytab}
            if ccache is not None:
                store["ccache"] = "FILE:" + ccache

            auth_args["creds"] = gssapi.Credentials(
                name=name, store=store, usage="initiate"
            )

        # We only do one request, but a Session is used to allow requests to write
        # the new session ID into the cookiejar.
        with requests.Session() as s:
            s.cookies = self._transport.cookiejar
            response = s.get(
                login_url,
                auth=requests_gssapi.HTTPSPNEGOAuth(**auth_args),
                allow_redirects=allow_redirects,
                **request_args
            )

        self._logger and self._logger.debug(
            "Login response: %s %s", response, response.headers
        )
        response.raise_for_status()

    def get_hub_hostname(self):
        """Get hub hostname out of hub url."""
        hostname = urlparse.urlparse(self._hub_url)[1]
        # remove port from hostname
        return hostname.split(":")[0]

    def get_server_principal(self, service=None, realm=None):
        """Convert hub url to kerberos principal."""
        hostname = self.get_hub_hostname()
        if realm is None:
            # guess realm: last two parts from hostname
            realm = ".".join(hostname.split(".")[-2:]).upper()
        if service is None:
            service = "HTTP"
        return '%s/%s@%s' % (service, hostname, realm)

    def upload_file(self, file_name, target_dir):
        scheme, netloc, path, params, query, fragment = urlparse.urlparse("%s/upload/" % self._hub_url)
        if ":" in netloc:
            host, port = netloc.split(":", 1)
        else:
            host, port = netloc, None

        sum = hashlib.sha256()
        fo = open(file_name, "rb")
        while True:
            chunk = fo.read(1024 ** 2)
            if not chunk:
                break
            sum.update(chunk)
        fo.close()
        checksum = sum.hexdigest().lower()

        fsize = os.path.getsize(file_name)
        # use str only for large uploads to not break compatibility with older hubs
        if fsize > xmlrpclib.MAXINT:
            fsize = str(fsize)

        upload_id, upload_key = self.upload.register_upload(os.path.basename(file_name), checksum, fsize, target_dir)

        secure = (scheme == "https")
        upload = kobo.http.POSTTransport()
        upload.add_variable("upload_id", upload_id)
        upload.add_variable("upload_key", upload_key)
        upload.add_file("file", file_name)

        err_code, err_msg = upload.send_to_host(host, path, port, secure)
        return upload_id, err_code, err_msg

    def upload_task_log(self, file_obj, task_id, remote_file_name, append=True, mode=0o644):
        """
        Upload a task log to the hub.

        @param file_obj: file object (or StringIO, etc.) with the log
        @type  file_obj: file
        @param task_id: task ID
        @type  task_id: int
        @param remove_file_name: relative path on hub to the log file
        @type  remove_file_name: str
        @param append: append at the end of existing file instead of rewriting it
        @type  append: bool
        @param mode: file perms (example: 0644)
        @type  mode: int
        """

        for (chunk_start, chunk_len, chunk_checksum, encoded_chunk) in kobo.xmlrpc.encode_xmlrpc_chunks_iterator(file_obj):
            if append:
                chunk_start = -1
                if chunk_len == -1:
                    # skip finializing chunk
                    break
            self._hub.worker.upload_task_log(task_id, remote_file_name, mode, chunk_start, chunk_len, chunk_checksum, encoded_chunk)


from xmlrpc.client import Fault

# default implementation of Fault.__repr__ is:
#    "<Fault %s: %s>" % (self.faultCode, repr(self.faultString))
# repr of string escapes everything (e.g. newlines) and produces a very ugly
# output so using it directly is much nicer for users
def fault_repr(self):
    return "<Fault %s: %s>" % (self.faultCode, self.faultString)

Fault.__repr__ = fault_repr
