from django.utils.unsetting import uses_settings
from django import http

class XViewMiddleware(object):
    """
    Adds an X-View header to internal HEAD requests -- used by the documentation system.
    """
    @uses_settings({'INTERNAL_IPS':'internal_ips'})
    def process_view(self, request, view_func, view_args, view_kwargs, internal_ips=()):
        """
        If the request method is HEAD and either the IP is internal or the
        user is a logged-in staff member, quickly return with an x-header
        indicating the view function.  This is used by the documentation module
        to lookup the view function for an arbitrary page.
        """
        assert hasattr(request, 'user'), (
            "The XView middleware requires authentication middleware to be "
            "installed. Edit your MIDDLEWARE_CLASSES setting to insert "
            "'django.contrib.auth.middleware.AuthenticationMiddleware'.")
        if request.method == 'HEAD' and (request.META.get('REMOTE_ADDR') in internal_ips or
                                         (request.user.is_active and request.user.is_staff)):
            response = http.HttpResponse()
            response['X-View'] = "%s.%s" % (view_func.__module__, view_func.__name__)
            return response
