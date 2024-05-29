import asyncio
import logging
import pyrc
from pyrc.errors import *  # noqa: F403
from pyrc.classes import *  # noqa: F403
from typing import Union, Dict, Callable, List, Tuple, Set


__doc__ = """
Main client module for pyirc. This should always be imported
"""


class IRCClient:
    def __init__(self, **kwargs):
        """
        Client class for setting up a connection to an IRC server
        :param kwargs: Keywords to pass into the IRCClient constructor
        """
        self.host: Union[None, str] = None
        self.port: Union[None, int] = None
        self.ctcpchar = bytes("\x01", "UTF-8")
        self.cmdbuf = []
        self.cmdwait = False
        self._reader: Union[None, asyncio.StreamReader] = None
        self._writer: Union[None, asyncio.StreamWriter] = None
        self.caps: List[str] = []
        self._events: Dict[str, List[Callable]] = {}
        self._task: Union[None, asyncio.Task] = None
        self.chmodemap: Dict[str, str] = {}
        self.channels: AsyncDict = AsyncDict()
        override_default_events: Union[None, Callable] = kwargs.get("override_default_events")
        if override_default_events:
            override_default_events(self)
            return
        pyrc.setup(self)
    
    async def get_channel(self, channel: str):
        """Gets the specified channel and associated userlist from the list of channels

        :param channel: The channel to get
        :return: The IRCChannel object, and the set of IRCUser objects, or None if the channel doesn't exist
        :rtype: Tuple[IRCChannel, Set[IRCUser]] | Tuple[None, None]
        """
        async for chan, users in self.channels:
            if channel == str(chan):
                return chan, users
        return None, None

    async def _dispatch_event(self, event: str, *args):
        """
        Event dispatcher for IRCClient
        :param event: Event to dispatch
        :param args: Args to pass into the callbacks
        """
        events = self._events.get("on_" + event.lower())
        if events is None:
            logging.debug(f"No events to call for event {event}")
            return
        for callback in events:
            logging.debug(f"Dispatching on_{event} to {len(events)} listeners")
            await callback(*args)

    def event(self, func, event = None):
        """
        Decorator to create a callback for events
        :param func: Coroutine to call when the event is raised
        :type func: coroutine
        :param event: Event name, if the coro's name is not the event name
        """
        evnt = func.__name__ if not event else event
        logging.debug(f"Registering callback for event {evnt}")
        if not asyncio.iscoroutinefunction(func):
            raise TypeError(f"Function \"{func.__name__}\" is type \"{type(func)}\", not a Coroutine")
        if self._events.get(evnt) is None:
            self._events[evnt] = [func]
        else:
            self._events[evnt].append(func)

    async def _loop(self):
        """
        Event loop for the client. This should not be invoked by anything other than IRCClient itself
        """
        while not self._writer.is_closing():
            try:
                data = await self._reader.readline()
                plaintext = data.decode().rstrip("\r\n")
                if plaintext == "":
                    return
                await self._dispatch_event("raw", plaintext)
                logging.debug(f"Received: {plaintext}")
                if plaintext.startswith("PING"):
                    await self.send(plaintext.replace("PING", "PONG"))
                    continue
                params = plaintext.split(" ", 2)
                author = IRCUser(params[0], self.chmodemap)
                verb = params[1]
                if verb in ["422", "376"]:
                    await self._dispatch_event("ready")
                    continue
                args = params[2]
                channel = None
                if args[0].startswith(":"):
                    msg = args
                else:
                    parse = args.split(" ")
                    for part in parse:
                        await asyncio.sleep(0)
                        if part.startswith(":"):
                            message = parse[parse.index(part):]
                            msg = " ".join(message)
                        if part.startswith("#"):
                            channel, _ = await self.get_channel(part)
                if verb == "PRIVMSG":
                    msg = msg.lstrip(":")
                    bmsg = bytes(msg, "UTF-8")
                    if bmsg.startswith(self.ctcpchar) and bmsg.endswith(self.ctcpchar):
                        bctcp = bmsg.strip(self.ctcpchar)
                        ctcp = bctcp.decode("UTF-8")
                        context = Context(plaintext, author, channel, msg, ctcp)
                        await self._dispatch_event("ctcp", context)
                        continue
                context = Context(plaintext, author, channel, msg)
                await self._dispatch_event(verb, context)
            except IndexError:
                print(f"Didn't understand {plaintext}", end="")
                continue
            except ConnectionResetError as e:
                logging.error("Connection lost.")
                await self._dispatch_event("disconnect")
                return

    async def send(self, message: str):
        """
        Send a raw message to an IRC server
        :param message: Raw IRC command to send
        :raises NotConnectedError: If the client is not actually connected yet
        """
        if self._writer is None:
            raise NotConnectedError("This IRCClient is not yet connected, call .connect first!")  # noqa: F405
        if self.cmdwait and not message.startswith("PONG"):
            logging.debug(f"Command \"{message}\" sent before connection was ready, deferring...")
            self.cmdbuf.append(message)
            return
        encoded_msg = bytes(message + "\r\n", "UTF-8")
        self._writer.write(encoded_msg)
        await self._writer.drain()
        logging.debug(f"Sent: {message}")

    async def connect(self, host: str, port: int, username: str, **kwargs):
        """
        Connects to the IRC server
        :param host: Hostname or IP for the IRCd
        :param port: Port number for the IRCd
        :param username: Username to use when authenticating with IRC
        :param kwargs: Additional args to pass to the client on connect
        """
        self.host = host
        self.port = port
        use_ssl = kwargs.get("ssl")
        nickname = kwargs.get("nick")
        password = kwargs.get("password")
        logging.info(f"Attempting to connect to IRCd at {host}:{'+' if use_ssl else ''}{port}")
        self._reader, self._writer = await asyncio.open_connection(self.host, self.port, ssl=use_ssl)
        self._task = asyncio.create_task(self._loop())
        realname = kwargs.get("realname")
        if nickname is None:
            nickname = username
        if password is not None:
            logging.debug("Attempting to authenticate with the provided password")
            await self.send(f"PASS {password}")
        await self.send(f"NICK {nickname}")
        await self.send(f"USER {username} 8 * :{realname if realname is not None else username}")
        await self._dispatch_event("connect")
        self.cmdwait = True
        

    async def disconnect(self, quit_message: str = None):
        """
        Immediately signals to the IRC server that the client is disconnecting and disconnects
        :param quit_message: The message to show on the IRCd. 'Quit' if no parameter is provided
        :return:
        """
        await self.send(f"QUIT :{quit_message if quit_message else 'Quit'}")
        self._writer.close()
        await self._task
        logging.info("Disconnected and loop closed.")
        await self._dispatch_event("disconnect")
    
    async def join_channel(self, channel: Union[str, List[str]]):
        """
        Joins a channel or list of channels
        :param channel: A string representing a channel, or a list of channels
        """
        if isinstance(channel, list):
            channels = " ".join(channel)
            await self.send(f"JOIN {channels}")
            return
        await self.send(f"JOIN {channel}")
    
    async def ctcpreply(self, nick: str, query: str, reply:str):
        """
        Reply to a received CTCP query from the given nick
        :param nick: The nick of the user who sent us the CTCP query
        :param query: The query they sent us, so we know what we're responding to
        :param reply: What we're responding with
        """
        await self.send(f"NOTICE {nick} \x01{query} {reply}\x01")
    
    async def ctcp(self, nick: str, query: str):
        """
        Send a CTCP query to the specified `nick`
        :param nick: The nickname of the user we are sending the CTCP to
        :param query: The query we are sending
        """
        await self.send(f"PRIVMSG {nick} :\x01{query}\x01")
    
    async def wait_for(self, event: str, check: Callable, timeout: float = 30):
        """Waits for a specified event to occur, and returns the result

        :param event: The name of the event to wait for
        :param check: A Callable that checks the context of the event and returns a bool
        :param timeout: Will raise a TimeoutError if the time is exceeded, defaults to 30
        :raises asyncio.TimeoutError: If the event is not triggered in time
        """
        result = False
        done = asyncio.Event()
        async def inner(context):
            nonlocal result
            if check(context):
                result = context
                done.set()
        self.event(inner, event)
        try:
            with asyncio.timeout(timeout):
                await done.wait()
        finally:
            self._events[event].remove(inner)
        return result