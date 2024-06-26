import asyncio
import pyrc
import logging


__doc__ = """
Default event handlers for IRCClient. These should be overridden with care as some of these handlers actually
do important things lib-side
"""


logger = logging.getLogger("defaulthandler")


class _DefaultEventHandlers:
    def __init__(self, client):
        """
        Class for handling default events in IRCClients
        :param client: IRCClient object
        """
        self.client = client

    async def on_353(self, ctx):
        """
        Default handler for numeric event 353 (NAME REPLY), creates and appends an IRCUser object to the channel's temporary channel list for later syncing
        """
        logger.debug(f"Received names for {ctx.channel.name}, caching")
        ctx.channel.is_caching = True
        preparse = ctx.raw.split(" = ")
        if len(preparse) == 1:
            preparse = ctx.raw.split(" * ")
        parse = preparse[1].split(" :")
        nicks = parse[1].split(" ")
        for nick in nicks:
            ctx.channel.cache.add(
                pyrc.IRCUser(nick, self.client.chmodemap, self.client)
            )
            await asyncio.sleep(0)

    async def on_366(self, ctx):
        """
        Default handler for numeric event 366 (END OF NAMES), causes the affected channel to sync its temporary userlist to the permanent userlist
        """
        logger.debug(f"End of names for {ctx.channel.name}, syncing")
        ctx.channel.sync()

    async def on_396(self, ctx):
        preparse = ctx.raw.split(" ")
        self.client.user.host = preparse[3]

    async def on_join(self, ctx):
        """
        Default handler for on_join, handles registering the channel with the client lib for IRCClient.get_channel
        """
        channelstr = ctx.message.lstrip(":")
        channels = channelstr.split(" ")
        logger.debug(f"Joined channel or channels: {channels}")
        for channel in channels:
            await asyncio.sleep(0)
            chan = pyrc.IRCChannel(channel, self.client)
            self.client.channels.add(chan)

    async def on_ready(self):
        """
        Event handler for on_ready, executes commands that were deferred during registration with the IRCd
        """
        self.client.cmdwait = False
        logger.info("Authenticated with IRCd, link becomes ready")
        logger.debug("Flushing deferred commands buffer")
        for message in self.client.cmdbuf:
            await self.client.send(message)
            await asyncio.sleep(1)
        self.client.cmdbuf = []


def setup(client):
    """
    Set up default events for IRCClients. This should be invoked during __init__ of an IRCClient class (or subclass)
    :param client: IRCClient to register the events with
    """
    default = _DefaultEventHandlers(client)
    for method in dir(default):
        if method.startswith("on_"):
            client.event(getattr(default, method))
