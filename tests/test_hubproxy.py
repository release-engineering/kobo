import pytest
import gssapi
import mock
import sys

from kobo.xmlrpc import SafeCookieTransport
from kobo.conf import PyConfigParser
from kobo.client import HubProxy


@pytest.fixture(autouse=True)
def requests_session():
    """Mocker for requests.Session; autouse to ensure no accidental real requests.

    Note the tests in this file can't be implemented using requests_mocker because that
    library doesn't track info about authentication.
    """
    with mock.patch("requests.Session") as s:
        # 'with requests.Session()' returns the session instance.
        s.return_value.__enter__.return_value = s.return_value
        yield s


class FakeTransport(SafeCookieTransport):
    """A fake XML-RPC transport where every request succeeds without doing anything.

    Subclasses the real SafeCookieTransport so we get a real CookieJar.
    """
    def __init__(self, *args, **kwargs):
        # note: py2 transport classes do not subclass object
        if sys.version_info[0] < 3:
            SafeCookieTransport.__init__(self, *args, **kwargs)
        else:
            super().__init__(*args, **kwargs)

        self.fake_transport_calls = []

    def request(self, host, path, request, verbose=False):
        self.fake_transport_calls.append((path, request))
        return []


def test_login_gssapi(requests_session):
    """Login with gssapi method obtains session cookie via SPNEGO & krb5login."""

    hub_url = "https://example.com/myapp/endpoint"
    login_url = "https://example.com/myapp/auth/krb5login/"

    conf = PyConfigParser()
    conf.load_from_dict(
        {"HUB_URL": hub_url, "AUTH_METHOD": "gssapi",}
    )

    transport = FakeTransport()
    proxy = HubProxy(conf, transport=transport)

    # Proxy might have already done some calls during initialization.
    # We're trying to test login in isolation, so keep track of how many
    # mock calls there have been already.
    mock_get = requests_session.return_value.get
    calls_before = len(mock_get.mock_calls)

    # Force a login
    proxy._login(force=True)

    # Cookies should have been shared between session and transport
    assert requests_session.return_value.cookies is transport.cookiejar

    # Check the requests done
    calls = mock_get.mock_calls[calls_before:]

    assert calls[0][0] == ""
    call_args = calls[0][1]
    call_kwargs = calls[0][2]

    # It should have made a request to log in
    assert call_args == (login_url,)

    # It should have enabled SPNEGO auth.
    # More details about this object are verified in a separate test.
    assert "HTTPSPNEGOAuth" in str(type(call_kwargs["auth"]))

    # It should have verified the result
    assert calls[1][0] == "().raise_for_status"

    # And that's all
    assert len(calls) == 2


def test_login_gssapi_krb_opts(requests_session):
    """Login with gssapi method prepares auth using correct gssapi parameters
    according to config."""

    hub_url = "https://hub.example.com/myapp/endpoint"
    login_url = "https://hub.example.com/myapp/auth/krb5login/"

    conf = PyConfigParser()
    conf.load_from_dict(
        {
            "HUB_URL": hub_url,
            "AUTH_METHOD": "gssapi",
            "CA_CERT": "/some/ca-bundle.pem",
            "KRB_PRINCIPAL": "someclient@EXAMPLE.COM",
            "KRB_SERVICE": "SVC",
            "KRB_REALM": "REALM.EXAMPLE.COM",
            "KRB_KEYTAB": "some-keytab",
            "KRB_CCACHE": "some-cache",
        }
    )

    transport = FakeTransport()
    proxy = HubProxy(conf, transport=transport)

    mock_get = requests_session.return_value.get
    calls_before = len(mock_get.mock_calls)

    with mock.patch("requests_gssapi.HTTPSPNEGOAuth") as mock_auth:
        with mock.patch("gssapi.Credentials") as mock_creds:
            # Force a login
            proxy._login(force=True)

    get_call = mock_get.mock_calls[calls_before]

    # It should have prepared credentials with the details from config
    mock_creds.assert_called_once_with(
        name=gssapi.Name("someclient@EXAMPLE.COM", gssapi.NameType.kerberos_principal),
        store={"client_keytab": "some-keytab", "ccache": "FILE:some-cache"},
        usage="initiate",
    )

    # It should have prepared auth with those credentials and our configured
    # server principal
    mock_auth.assert_called_once_with(
        creds=mock_creds.return_value,
        target_name=gssapi.Name(
            "SVC/hub.example.com@REALM.EXAMPLE.COM", gssapi.NameType.kerberos_principal
        ),
    )

    # It should have used the configured CA bundle when issuing the request
    assert get_call[2]["verify"] == "/some/ca-bundle.pem"


def test_login_gssapi_principal_needs_keytab(requests_session):
    """Login with gssapi method raises if principal is provided without keytab."""
    hub_url = "https://hub.example.com/myapp/endpoint"

    conf = PyConfigParser()
    conf.load_from_dict(
        {
            "HUB_URL": hub_url,
            "AUTH_METHOD": "gssapi",
            "KRB_PRINCIPAL": "someclient@EXAMPLE.COM",
        }
    )

    transport = FakeTransport()
    logger = mock.Mock()
    proxy = HubProxy(conf, transport=transport, logger=logger)

    proxy._login(force=True)

    # This is pretty dumb: login() swallows all exceptions (probably for no good reason).
    # The only hint there was a problem is a DEBUG log message, so we detect the error
    # that way.
    logger.debug.assert_called_with(
        "Failed to create new session: Cannot specify a principal without a keytab"
    )


def test_no_auto_logout(requests_session):
    """auto_logout argument warns of deprecation"""
    conf = PyConfigParser()
    conf.load_from_dict({"HUB_URL": 'https://example.com/hub'})

    transport = FakeTransport()
    with pytest.deprecated_call():
        HubProxy(conf, transport=transport, auto_logout=True)


def test_proxies_to_xmlrpc(requests_session):
    """HubProxy proxies to underlying XML-RPC ServerProxy"""
    conf = PyConfigParser()
    conf.load_from_dict({"HUB_URL": 'https://example.com/hub'})

    transport = FakeTransport()
    proxy = HubProxy(conf, transport=transport)

    proxy.some_obj.some_method()

    # Last call should have invoked the method I requested
    (_, request_xml) = transport.fake_transport_calls[-1]
    assert b'some_obj.some_method' in request_xml
