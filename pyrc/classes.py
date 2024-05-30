import logging
import re
import asyncio
from typing import Dict, Union


__doc__ = """
Commonly used classes for pyirc. These classes shouldn't be instantiated by the user
"""


class AsyncDict(dict):
    """
    Dictionary supporting asynchronous iteration to avoid blocking running event loops
    """
    async def __aiter__(self):
        for key, value in self.items():
            await asyncio.sleep(0)
            yield key, value


class IRCUser:
    """
    Object denoting an IRC user
    :param user_string: The string that identifies the user (either nick or nick!user@host)
    :param chmapping: The channel mode mapping for the server this user originates from
    """
    def __init__(self, user_string: str, chmapping: Dict[str, str]):
        self.raw = user_string
        self.raw.lstrip(":")
        self.chmapping = chmapping
        self.nick, self.user, self.host = re.search(r"^(\S+?)(?:!(\S+?)@(\S+))?$", self.raw).groups()
        self.nick = self.nick.lstrip(":")
        if self.user is not None:
            self.chmodes = self._get_chmodes()
            self.user.lstrip("".join(self.chmodes))

    def __str__(self):
        return self.nick

    def __hash__(self):
        return hash(self.raw)

    def __eq__(self, other):
        return hash(self) == hash(other) if type(other) is type(self) else False

    def _get_chmodes(self, modes: list | None = None, next_ind: int = 0):
        """
        Recursively walks the user's nickname until all prefixes for this user have been found
        :param modes: The modes found on the user so far, or None
        :next_ind: the index to check. This should be +1 for every iteration to avoid infinite recursions
        """
        modes = [] if modes is None else modes
        if self.raw[next_ind] in self.chmapping.values():
            modes.append(self.raw[next_ind])
            modes = self._get_chmodes(modes, next_ind + 1)
            return modes
        return modes


class IRCChannel:
    """
    Class denoting an IRC server channel
    :param name: The name of the channel. Additional data will be added to the channel when it becomes available
    """
    def __init__(self, name: str):
        self.name = name
        self.chmodes = None
        self.is_caching = False
        self.users = set()
        self.cache = set()

    def sync(self):
        """
        Sync the cached (temporary) userlist to the permanent userlist. Will do nothing if the channel is not marked as actively caching
        """
        if not self.is_caching:
            logging.warning(f"IRCChannel {self} is not caching. refused to sync")
            return
        self.users = self.cache.copy()
        self.cache.clear()
        self.is_caching = False
    
    def __str__(self):
        return self.name

class Context:
    """
    Event context class for event callbacks
    :param raw: The raw command string, if the callback needs to parse it further
    :param author: The IRCUser object of the person who caused this event
    :param channel: The channel that this command targets, if any
    :param message: The trailer of the command (May be an actual message, or a parameter that includes spaces)
    :param ctcp: The CTCP query string found in the message, if any. Will only be present if the command is a PRIVMSG, per spec
    :cvar raw: The raw string that triggered this event
    :cvar author: The IRCUser that triggered this event, if any
    :cvar channel: The IRCChannel this event was triggered in, if any
    :cvar message: The trailer for the event (is not always a message), if any
    :cvar ctcp: The CTCP data in this event, if any
    """
    def __init__(
        self,
        raw: str,
        author: Union[IRCUser, None] = None,
        channel: Union[IRCChannel, None] = None,
        message: Union[str, None] = None,
        ctcp: Union[str, None] = None
    ):
        self.author = author
        self.channel = channel
        self.message = message
        self.raw = raw
        self.ctcp = ctcp
