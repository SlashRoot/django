"""
A set of request processors that return dictionaries to be merged into a
template context. Each function takes the request object as its only parameter
and returns a dictionary to add to the context.

These are referenced from the setting TEMPLATE_CONTEXT_PROCESSORS and used by
RequestContext.
"""
from __future__ import unicode_literals

from django.utils.unsetting import uses_settings
from django.middleware.csrf import get_token
from django.utils import six
from django.utils.encoding import smart_text
from django.utils.functional import lazy


def csrf(request):
    """
    Context processor that provides a CSRF token, or the string 'NOTPROVIDED' if
    it has not been provided by either a view decorator or the middleware
    """
    def _get_val():
        token = get_token(request)
        if token is None:
            # In order to be able to provide debugging info in the
            # case of misconfiguration, we use a sentinel value
            # instead of returning an empty dict.
            return 'NOTPROVIDED'
        else:
            return smart_text(token)
    _get_val = lazy(_get_val, six.text_type)

    return {'csrf_token': _get_val() }

@uses_settings({'DEBUG':'debug', 'INTERNAL_IPS':'internal_ips'})
def debug(request, debug=False, internal_ips=()):
    "Returns context variables helpful for debugging."
    context_extras = {}
    if debug and request.META.get('REMOTE_ADDR') in internal_ips:
        context_extras['debug'] = True
        from django.db import connection
        context_extras['sql_queries'] = connection.queries
    return context_extras

@uses_settings({'LANGUAGES':'languages'})
def i18n(request, languages=()):
    from django.utils import translation

    context_extras = {}
    context_extras['LANGUAGES'] = languages
    context_extras['LANGUAGE_CODE'] = translation.get_language()
    context_extras['LANGUAGE_BIDI'] = translation.get_language_bidi()

    return context_extras

def tz(request):
    from django.utils import timezone

    return {'TIME_ZONE': timezone.get_current_timezone_name()}

@uses_settings({'STATIC_URL':'static_url'})
def static(request, static_url=None):
    """
    Adds static-related context variables to the context.

    """
    return {'STATIC_URL': static_url}

@uses_settings({'MEDIA_URL':'media_url'})
def media(request, media_url=''):
    """
    Adds media-related context variables to the context.

    """
    return {'MEDIA_URL': media_url}

def request(request):
    return {'request': request}
