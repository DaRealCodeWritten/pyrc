

__doc__ = """
Errors raised by IRCClient or its subordinate modules. This should only be imported for the purpose of
defining error handlers in client-side code
"""


class NotConnectedError(Exception):
    pass

class JoinChannelFailed(Exception):
    pass

class ExtensionFailed(Exception):
    pass

class ExtensionNotFound(Exception):
    pass
