import asyncio
import logging
import pyrc
import ssl
import traceback
import importlib
from pyrc.errors import *  # noqa: F403
from pyrc.classes import *  # noqa: F403
from pyrc.ext import extension
from pyrc.util import authhelper
from typing import Union, Dict, Callable, List, Literal, Optional, Tuple


__doc__ = """
Main client module for pyirc. This should always be imported
"""


logger = logging.getLogger("client")


class IRCClient:
    r"""
    Client class for setting up a connection to an IRC server
    :ivar host: a string representing the host that the client is connected to
    :ivar port: the port number the client is connected to
    """

    def __init__(self, **kwargs):
        self._events: Dict[str, List[Callable]] = {}
        self._task: Union[None, asyncio.Task] = None
        self._reader: Union[None, asyncio.StreamReader] = None
        self._writer: Union[None, asyncio.StreamWriter] = None
        self._named_events = {}
        self._exts: Dict[str, extension.Extension] = {}
        self._depmap: Dict[str, List[extension.Extension]] = {}
        self.host: Union[None, str] = None
        self.port: Union[None, int] = None
        self.ctcpchar: bytes = bytes("\x01", "UTF-8")
        self.cmdbuf: List[str] = []
        self.cmdwait: bool = False
        self.user: Union[IRCUser, None] = None
        self.chmodemap: Dict[str, str] = {}
        self.channels: set = set()
        override_default_events: Union[None, Callable] = kwargs.get(
            "override_default_events"
        )
        self.load_behavior: Union[Literal["lazy"], Literal["active"]] = kwargs.get(
            "loading", "lazy"
        )
        self.capabilities: Dict[str, Union[None, List[str]]] = {}
        self.parser: Callable = self.parse
        if override_default_events:
            override_default_events(self)
            return
        pyrc.setup(self)

    def add_module(self, module):
        """Adds and loads a new module to the client ecosystem

        :param module: The module instance to load
        :type module: pyrc.ext.extension.Extension
        :raises ExtensionFailed: If the module could not be initialized
        """
        for cap in module.depends:
            if self._depmap.get(cap) is None:
                for cap in module.depends:
                    self._depmap.pop(cap, None)
                raise ExtensionFailed(
                    f"Module '{module.__name__}' failed to load. One or more dependencies was not met"
                )
            module.interfaces[cap] = self._exts.get(cap)
        for prov in module.provides:
            self._depmap.setdefault(prov, [])
        self._exts[module.name] = module

    async def remove_module(self, module_name: str):
        """Removes a given module from the client

        :param module_name: The module name to look for and remove
        :raises ExtensionNotFound: If the module is not found
        """
        mod = self._exts.get(module_name)
        if mod is None:
            raise ExtensionNotFound(
                f"Module '{module_name}' is either not loaded, or partially initialized"
            )
        self._exts.pop(module_name)
        for dep in mod.depends:
            await asyncio.sleep(0)
            self._depmap[dep].remove(mod)
        for prov in mod.provides:
            await asyncio.sleep(0)
            for other in self._depmap[prov]:
                await asyncio.sleep(0)
                await self.remove_module(other.name)
            self._depmap.pop(prov)
        await mod.teardown()

    async def _get_named_event(self, verb: str):
        """Gets a named event for use in event dispatching

        :param verb: The raw verb to convert
        :return: The named event matching the verb, or the verb if no named event exists
        """
        for keys, value in self._named_events.items():
            await asyncio.sleep(0)
            if verb in keys:
                return value
        return verb

    async def register_caps(self, caps: List[str]):
        capabilities = {}
        for cap in caps:
            await asyncio.sleep(0)
            breakdown = cap.split("=")
            if len(breakdown) > 1:
                args = breakdown[1].split(",")
                capabilities[breakdown[0]] = args
                self._depmap.setdefault(cap, [])
                continue
            capabilities[cap] = None
        return capabilities

    async def parse(self, message: str):
        """Parses a message, and returns the event name and Context (if the event takes a Context)

        :param message: The raw server message to parse
        :return: The event name, and the Context if applicable

        """
        params = message.split(" ", 2)
        author = IRCUser(params[0], self.chmodemap, self)
        verb = params[1]
        if verb in [
            "422",
            "376",
        ]:  # MOTD or NOMOTD verbs, this means that the connection has registered and on_ready can be emitted
            yield "ready", None
        args = params[2]
        channel = None
        msg = None
        if args[0].startswith(":"):
            msg = args
        else:
            parse = args.split(" ")
            for part in parse:
                await asyncio.sleep(0)
                if part.startswith(":"):
                    messag = parse[parse.index(part) :]
                    msg = " ".join(messag)
                    break
                if part.startswith("#"):
                    channel = await self.get_channel(part)
            if verb == "PRIVMSG":
                msg = msg.lstrip(":")
                bmsg = bytes(msg, "UTF-8")
                if bmsg.startswith(self.ctcpchar) and bmsg.endswith(self.ctcpchar):
                    bctcp = bmsg.strip(self.ctcpchar)
                    ctcp = bctcp.decode("UTF-8")
                    context = Context(message, author, channel, msg, ctcp)
                    yield "ctcp", context
                    return
        named = await self._get_named_event(verb)
        context = Context(
            message, author, channel, msg, None, named if named != verb else None
        )
        if verb.isnumeric():
            yield "nnn", context
        yield named, context

    async def get_channel(self, channel: str):
        """Gets the specified channel from the set of channels

        :param channel: The channel to get
        :return: The IRCChannel object, or None if it doesn't exist
        :rtype: IRCChannel | None
        """
        for chan in self.channels:
            await asyncio.sleep(0)
            if str(chan) == channel:
                return chan
        return None

    async def _dispatch_event(self, event: str, *args):
        """
        Event dispatcher for IRCClient
        :param event: Event to dispatch
        :param args: Args to pass into the callbacks
        """
        events = self._events.get("on_" + event.lower())
        if events is None:
            logger.debug(f"No events to call for event {event}")
            return
        logger.debug(f"Dispatching on_{event} to {len(events)} listeners")
        try:
            results = await asyncio.gather(*(callback(*args) for callback in events), return_exceptions=True)
            for result in results:
                if issubclass(result, Exception):
                    logger.error("Ignoring exception thrown in event callback")
        except Exception as e:
            logger.error(
                f"Ignoring exception thrown while dispatching on_{event.lower()}", exc_info=1
            )

    def event(self, func, events: Union[str, List[str], None] = None):
        """
        Decorator to create a callback for events
        :param func: Coroutine to call when the event is raised
        :type func: coroutine
        :param events: Event name(s), if the coro's name is not the event name
        """
        evnt = func.__name__ if not events else events
        logger.debug(f"Registering callback for event(s) {evnt}")
        if not asyncio.iscoroutinefunction(func):
            raise TypeError(
                f'Function "{func.__name__}" is type "{type(func)}", not a Coroutine'
            )
        if isinstance(evnt, list):
            for event in evnt:
                self._events.setdefault(event, []).append(func)
            return
        self._events.setdefault(evnt, []).append(func)

    def remove_event(self, event_name: str, func: Callable):
        events = self._events.get(event_name)
        try:
            events.remove(func)
            return True
        except ValueError:
            return False

    async def _loop(self):
        """
        Event loop for the client. This should not be invoked by anything other than IRCClient itself
        """
        while not self._writer.is_closing():
            try:
                data = await self._reader.readline()
                plaintext = data.decode().rstrip("\r\n")
                if (
                    plaintext == ""
                ):  # No data, the connection is probably closed, so the loop can end
                    return
                await self._dispatch_event("raw", plaintext)
                logger.debug(f"Received: {plaintext}")
                if plaintext.startswith("PING"):  # Respond to PINGs with PONGs
                    await self.send(plaintext.replace("PING", "PONG"))
                    continue
                async for event, ctx in self.parser(plaintext):
                    if ctx:
                        await self._dispatch_event(event, ctx)
                        continue
                    await self._dispatch_event(event)
            except IndexError as e:
                logger.error(f"Didn't understand {plaintext}", exc_info=1)
                continue
            except ConnectionResetError:
                logger.error("Connection lost.")
                await self._dispatch_event("disconnect")
                return
            except Exception as e:
                print("\n".join(traceback.format_exception(e)))
                await self.disconnect("Library error. Disconnected")

    async def send(self, message: str):
        """
        Send a raw message to an IRC server
        :param message: Raw IRC command to send
        :raises NotConnectedError: If the client is not actually connected yet
        """
        if self._writer is None:
            raise NotConnectedError(
                "This IRCClient is not yet connected, call .connect first!"
            )  # noqa: F405
        if self.cmdwait and not message.startswith("PONG"):
            logger.debug(
                f'Command "{message}" sent before connection was ready, deferring...'
            )
            self.cmdbuf.append(message)
            return
        encoded_msg = bytes(message + "\r\n", "UTF-8")
        self._writer.write(encoded_msg)
        await self._writer.drain()
        logger.debug(f"Sent: {message}")

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
        authmethods = {
            "ns": authhelper.ns_authenticate,
            "sasl": authhelper.sasl_authenticate,
        }
        use_ssl = kwargs.get("ssl")
        nickname = kwargs.get("nick")
        password = kwargs.get("password")
        realname = kwargs.get("realname")
        caps = kwargs.get("capabilities")
        callbacks = kwargs.get("callbacks")
        method = kwargs.get("auth_method")
        authargs = kwargs.get("auth_params")
        chmodemap = kwargs.get("chmodes", {})
        logger.info(
            f"Attempting to connect to IRCd at {host}:{'+' if use_ssl else ''}{port}"
        )
        sslobj = None
        if use_ssl is True:
            sslobj = ssl.create_default_context()
        self._reader, self._writer = await asyncio.open_connection(
            self.host, self.port, ssl=sslobj
        )
        self._task = asyncio.create_task(self._loop())
        realname = kwargs.get("realname")
        caps = kwargs.get("capabilities")
        if caps is not None:
            await self.send("CAP LS 302")
        if nickname is None:
            nickname = username
        if password is not None:
            logger.debug("Attempting to authenticate with the provided password")
            await self.send(f"PASS {password}")
        await self.send(f"NICK {nickname}")
        await self.send(
            f"USER {username} 0 * :{realname if realname is not None else username}"
        )
        await self._dispatch_event("connect")
        if caps is not None:
            serv = await self.wait_for("on_cap")
            servcaps = await self.register_caps(serv.message.lstrip(":").split(" "))
            negotiate = []
            for cap in caps:
                if cap in servcaps.keys():
                    negotiate.append(cap)
            await self.send(f"CAP REQ :{' '.join(negotiate)}")
            capresp = await self.wait_for("on_cap")
            self.capabilities = await self.register_caps(
                capresp.message.lstrip(":").split(" ")
            )
        if method and authargs:
            func = authmethods.get(method)
            assert func
            await func(self, *authargs)
        else:
            await self.send("CAP END")
        self.chmodemap = chmodemap
        self.user = IRCUser(nickname, self.chmodemap, self)
        if callbacks is not None:
            for cb in callbacks:
                await cb(self)
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
        logger.info("Disconnected and loop closed.")
        await self._dispatch_event("disconnect")

    async def join_channel(self, channel: Union[str, List[str]]):
        """
        Joins a channel or list of channels
        :param channel: A string representing a channel, or a list of channels
        :return: An IRCChannel or list of IRCChannels. One or more channels will be None if joining a channel failed
        :rtype: Iterable[IRCChannel | None]
        """
        if isinstance(channel, list):
            for chan in channel:
                try:
                    await self.send(f"JOIN {chan}")
                    res = await self.wait_for(
                        ["on_join", "on_join_fail"],
                        lambda ctx: str(ctx.channel) in [None, chan],
                    )
                    if res.event == "join_fail":
                        yield None
                    yield res.channel
                except asyncio.TimeoutError:
                    yield None
                    continue
            return
        await self.send(f"JOIN {channel}")
        try:
            res = await self.wait_for(
                ["on_join", "on_join_fail"],
                lambda ctx: str(ctx.channel) in [None, channel],
            )
            if res.event == "join_fail":
                yield None
            yield res.channel
        except asyncio.TimeoutError:
            yield None

    async def ctcpreply(self, nick: str, query: str, reply: str):
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

    async def wait_for(
        self,
        event: Union[str, list],
        check: Callable = lambda args: True,
        timeout: float = 30,
    ):
        """Waits for a specified event to occur, and returns the result

        :param event: The name (or names) of the event(s) to wait for. Returns the first event that matches
        :param check: A Callable that checks the context of the event and returns a bool
        :param timeout: Will raise a TimeoutError if the time is exceeded, defaults to 30
        :raises asyncio.TimeoutError: If the event is not triggered in time
        :return: The Context of the event that passed `check`
        :rtype: pyrc.Context | False
        """
        result = False
        done = asyncio.Event()

        async def inner(context=None):
            nonlocal result
            if check(context):
                result = context
                done.set()

        self.event(inner, event)
        try:
            async with asyncio.timeout(timeout):
                await done.wait()
        finally:
            if isinstance(event, list):
                for evnt in event:
                    await asyncio.sleep(0)
                    self._events[evnt].remove(inner)
                return result
            self._events[event].remove(inner)
        return result

    async def load_extension(self, ext: str):
        """Load an extension

        :param ext: The import name of the module (e.g. cogs.myextension to import myextension from the cogs/ folder)
        :raises ExtensionFailed: If the extension couldn't be loaded
        """
        try:
            mod = importlib.import_module(ext)
            mod.setup(self, ext)
            logger.debug(f"Extension '{ext}' was successfully set up")
        except ModuleNotFoundError as e:
            raise ExtensionFailed(
                f"Extension '{ext}' could not be loaded: Module not found"
            ) from e
        except AttributeError as e:
            raise ExtensionFailed(
                f"Extension '{ext}' does not implement a 'setup' function"
            ) from e

    async def unload_extension(self, ext: str):
        """Unloads the given extension

        :param ext: The extension to unload
        """
        for name, mod in self._exts:
            if mod.importby == ext:
                await self.remove_module(name)
