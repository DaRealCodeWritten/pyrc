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


class IRCObjectSendable:
    """
    Object class for IRC objects, implements a send() method for sending messages that target this object
    :param client: IRCClient object that this object is bound to
    :param sendable: A string that denotes the PRIVMSG/NOTICE target
    """

    def __init__(self, client, sendable: str):
        self.client = client
        self.sendable = sendable

    async def send(self, message: str):
        """Sends a message to the target of this IRC object

        :param message: The message to send
        """
        await self.client.send(f"PRIVMSG {self.sendable} :{message}")


class IRCUser(IRCObjectSendable):
    """
    Object denoting an IRC user
    :param user_string: The string that identifies the user (either nick or nick!user@host)
    :param chmapping: The channel mode mapping for the server this user originates from
    :param client: The IRCClient that instantiated this IRCUser
    :ivar raw: The raw userstring for this User
    :ivar nick: The nickname of this User
    :ivar host: The host/vhost of this User, may be None if this user is lazily loaded (default)
    :ivar user: The username of this User, may be None if this user is lazily loaded (default)
    """

    def __init__(self, user_string: str, chmapping: Dict[str, str], client):
        self.raw = user_string
        self.raw.lstrip(":")
        self.chmapping = chmapping
        res = re.search(r"^(\S+?)(?:!(\S+?)@(\S+))?$", self.raw)
        self.nick, self.user, self.host = (
            res.groups() if res is not None else [user_string, None, None]
        )
        self.nick = self.nick.lstrip(":")
        if self.user is not None:
            self.chmodes = self._get_chmodes()
            self.user.lstrip("".join(self.chmodes))
        super().__init__(client, self.nick)

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
        :param next_ind: the index to check. This should be +1 for every iteration to avoid infinite recursions
        """
        modes = [] if modes is None else modes
        if self.raw[next_ind] in self.chmapping.values():
            modes.append(self.raw[next_ind])
            modes = self._get_chmodes(modes, next_ind + 1)
            return modes
        return modes


class IRCChannel(IRCObjectSendable):
    """
    Class denoting an IRC server channel
    :param name: The name of the channel. Additional data will be added to the channel when it becomes available
    :param client: The IRCClient that instantiated this IRCChannel
    :ivar name: The name of this channel
    :ivar chmodes: The channel modes for this channel, may be None if lazyloading (default)
    :ivar users: A set of IRCUser objects in this channel
    :type users: Set[IRCUser]
    """

    def __init__(self, name: str, client):
        self.name = name
        self.chmodes = None
        self.is_caching = False
        self.users = set()
        self.cache = set()
        super().__init__(client, self.name)

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
    :param event: The event that instantiated this Context
    :ivar raw: The raw string that triggered this event
    :ivar author: The IRCUser that triggered this event, if any
    :ivar channel: The IRCChannel this event was triggered in, if any
    :ivar message: The trailer for the event (is not always a message), if any
    :ivar ctcp: The CTCP data in this event, if any
    """

    def __init__(
        self,
        raw: str,
        author: Union[IRCUser, None] = None,
        channel: Union[IRCChannel, None] = None,
        message: Union[str, None] = None,
        ctcp: Union[str, None] = None,
        event: Union[str, None] = None,
    ):
        self.author = author
        self.channel = channel
        self.message = message
        self.raw = raw
        self.ctcp = ctcp
        self.event = event
