'''
This module defines a series of Sorna-specific errors based on HTTP Error
classes from aiohttp.
Raising a SornaError automatically is automatically mapped to a corresponding
HTTP error response with RFC7807-style JSON-encoded description in its response
body.

In the client side, you should use "type" field in the body to distinguish
canonical error types beacuse "title" field may change due to localization and
future UX improvements.
'''

import sys

from aiohttp import web
import simplejson as json


class SornaError(web.HTTPError):
    '''
    An RFC-7807 error class as a drop-in replacement of the original
    aiohttp.web.HTTPError subclasses.
    '''

    status_code = 500
    error_type  = 'https://api.sorna.io/probs/general-error'
    error_title = 'General Sorna API Error.'

    def __init__(self, extra_msg=None):
        super().__init__()
        self.args = (self.status_code, self.reason, self.error_type)
        self.empty_body = False
        self.content_type = 'application/problem+json'
        if extra_msg:
            self.error_title += f' ({extra_msg})'
        self.body = json.dumps({
            'type': self.error_type,
            'title': self.error_title,
        }).encode()


class GenericNotFound(web.HTTPNotFound, SornaError):
    error_type  = 'https://api.sorna.io/probs/generic-not-found'
    error_title = 'Unknown URL path.'


class GenericBadRequest(web.HTTPNotFound, SornaError):
    error_type  = 'https://api.sorna.io/probs/generic-bad-request'
    error_title = 'Bad request.'


class InternalServerError(web.HTTPInternalServerError, SornaError):
    error_type  = 'https://api.sorna.io/probs/internal-server-error'
    error_title = 'Internal server error.'


class ServiceUnavailable(web.HTTPServiceUnavailable, SornaError):
    error_type  = 'https://api.sorna.io/probs/service-unavailable'
    error_title = 'Serivce unavailable.'


class QueryNotImplemented(web.HTTPServiceUnavailable, SornaError):
    error_type  = 'https://api.sorna.io/probs/not-implemented'
    error_title = 'This API query is not implemented.'


class InvalidAuthParameters(web.HTTPBadRequest, SornaError):
    error_type  = 'https://api.sorna.io/probs/invalid-auth-params'
    error_title = 'Missing or invalid authorization parameters.'


class AuthorizationFailed(web.HTTPUnauthorized, SornaError):
    error_type  = 'https://api.sorna.io/probs/auth-failed'
    error_title = 'Credential/signature mismatch.'


class InvalidAPIParameters(web.HTTPBadRequest, SornaError):
    error_type  = 'https://api.sorna.io/probs/invalid-api-params'
    error_title = 'Missing or invalid API parameters.'


class InstanceNotFound(web.HTTPNotFound, SornaError):
    error_type  = 'https://api.sorna.io/probs/instance-not-found'
    error_title = 'No such instance.'


class KernelNotFound(web.HTTPNotFound, SornaError):
    error_type  = 'https://api.sorna.io/probs/kernel-not-found'
    error_title = 'No such kernel.'


class QuotaExceeded(web.HTTPPreconditionFailed, SornaError):
    error_type  = 'https://api.sorna.io/probs/quota-exceeded'
    error_title = 'You have reached your resource limit.'


class RateLimitExceeded(web.HTTPTooManyRequests, SornaError):
    error_type  = 'https://api.sorna.io/probs/rate-limit-exceeded'
    error_title = 'You have reached your API query rate limit.'


class InstanceNotAvailable(web.HTTPServiceUnavailable, SornaError):
    error_type  = 'https://api.sorna.io/probs/instance-not-available'
    error_title = 'There is no available instance.'


class AgentError(RuntimeError):
    '''
    A dummy exception class to distinguish agent-side errors passed via
    aiozmq.rpc calls.

    It carrise two args tuple: the exception type and exception arguments from
    the agent.
    '''
    pass


class SornaAgentError(SornaError):
    '''
    An RFC-7807 error class that wraps agent-side errors.
    '''

    _short_type_map = {
        'TIMEOUT': 'https://api.sorna.io/probs/agent-timeout',
        'INVALID_INPUT': 'https://api.sorna.io/probs/agent-invalid-input',
        'FAILURE': 'https://api.sorna.io/probs/agent-failure',
    }

    def __init__(self, agent_error_type, exc_info=None):
        super().__init__()
        if not agent_error_type.startswith('https://'):
            agent_error_type = self._short_type_map[agent_error_type.upper()]
        self.args = (self.status_code, self.reason, self.error_type, agent_error_type)
        if isinstance(exc_info, str):
            agent_error_title = exc_info
            agent_details = {
                'type': agent_error_type,
                'title': agent_error_title,
            }
        elif isinstance(exc_info, AgentError):
            if isinstance(exc_info.args[0], Exception):
                inner_name = type(exc_info.args[0]).__name__
            elif issubclass(exc_info.args[0], Exception):
                inner_name = exc_info.args[0].__name__
            else:
                inner_name = str(exc_info.args[0])
            inner_args = ', '.join(repr(a) for a in exc_info.args[1])
            agent_error_title = 'Agent-side exception occurred.'
            agent_details = {
                'type': agent_error_type,
                'title': agent_error_title,
                'exception': f"{inner_name}({inner_args})",
            }
        elif isinstance(exc_info, Exception):
            agent_error_title = 'Unexpected exception ocurred.'
            agent_details = {
                'type': agent_error_type,
                'title': agent_error_title,
                'exception': repr(exc_info),
            }
        else:
            agent_error_title = None if exc_info is None else str(exc_info)
            agent_details = {
                'type': agent_error_type,
                'title': agent_error_title,
            }
        self.agent_error_type = agent_error_type
        self.agent_error_title = agent_error_title
        self.body = json.dumps({
            'type': self.error_type,
            'title': self.error_title,
            'agent-details': agent_details,
        }).encode()


class KernelCreationFailed(web.HTTPInternalServerError, SornaAgentError):
    error_type  = 'https://api.sorna.io/probs/kernel-creation-failed'
    error_title = 'Kernel creation has failed.'


class KernelDestructionFailed(web.HTTPInternalServerError, SornaAgentError):
    error_type  = 'https://api.sorna.io/probs/kernel-destruction-failed'
    error_title = 'Kernel destruction has failed.'


class KernelRestartFailed(web.HTTPInternalServerError, SornaAgentError):
    error_type  = 'https://api.sorna.io/probs/kernel-restart-failed'
    error_title = 'Kernel restart has failed.'


class KernelExecutionFailed(web.HTTPInternalServerError, SornaAgentError):
    error_type  = 'https://api.sorna.io/probs/kernel-execution-failed'
    error_title = 'Executing user code in the kernel has failed.'
