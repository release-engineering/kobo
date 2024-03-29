# -*- coding: utf-8 -*-


# Based on http://code.djangoproject.com/wiki/XML-RPC
#
# Credits:
#       Brendan W. McAdams


import sys
import six.moves.xmlrpc_client as xmlrpclib
from six.moves.xmlrpc_server import SimpleXMLRPCDispatcher

from django.conf import settings


__all__ = (
    'DjangoXMLRPCDispatcher',
)


class DjangoXMLRPCDispatcher(SimpleXMLRPCDispatcher):
    def __init__(self, allow_none=True, encoding=None):
        SimpleXMLRPCDispatcher.__init__(self, allow_none, encoding)

        self.allow_none = allow_none
        self.encoding = encoding
        self.register_multicall_functions()


    def system_multicall(self, request, call_list):
        for call in call_list:
            # insert request to each param list
            call['params'] = [request] + call['params']

        return SimpleXMLRPCDispatcher.system_multicall(self, call_list)


    def register_module(self, module_name, function_prefix):
        """register all the public functions in a module with prefix prepended"""

        if type(module_name) is str:
            module = __import__(module_name, {}, {}, [""])
        else:
            module = module_name

        if hasattr(module, '__all__'):
            fn_list = module.__all__
        else:
            fn_list = dir(module)

        for fn in fn_list:
            if fn.startswith("_"):
                continue

            function = getattr(module, fn)
            if not callable(function):
                continue

            name = fn
            if function_prefix:
                name = "%s.%s" % (function_prefix, name)
            name = name.replace("__", ".")

            self.register_function(function, name)


    def _marshaled_dispatch(self, request, dispatch_method = None):
        """Dispatches an XML-RPC method from marshalled (XML) data.

        XML-RPC methods are dispatched from the marshalled (XML) data
        using the _dispatch method and the result is returned as
        marshalled data. For backwards compatibility, a dispatch
        function can be provided as an argument (see comment in
        SimpleXMLRPCRequestHandler.do_POST) but overriding the
        existing method through subclassing is the prefered means
        of changing method dispatch behavior.
        """

        data = request.body
        params, method = xmlrpclib.loads(data)

        # add request to params
        params = (request, ) + params

        # generate response
        try:
            if dispatch_method is not None:
                response = dispatch_method(method, params)
            else:
                response = self._dispatch(method, params)
            # wrap response in a singleton tuple
            response = (response,)
            response = xmlrpclib.dumps(response, methodresponse=1, allow_none=self.allow_none, encoding=self.encoding)

        except xmlrpclib.Fault as fault:
            response = xmlrpclib.dumps(fault, allow_none=self.allow_none, encoding=self.encoding)

        except:
            # report exception back to server
            if settings.DEBUG:
                from kobo.tback import Traceback
                response = xmlrpclib.dumps(
                    xmlrpclib.Fault(1, u"%s" % Traceback().get_traceback()),
                    allow_none=self.allow_none, encoding=self.encoding)
            else:
                exc_info = sys.exc_info()[1]
                exc_type = exc_info.__class__.__name__
                response = xmlrpclib.dumps(
                    xmlrpclib.Fault(1, "%s: %s" % (exc_type, exc_info)),
                    allow_none=self.allow_none, encoding=self.encoding)

        return response
