import asyncio
import pyrc


__doc__ = """
Default event handlers for IRCClient. These should be overridden with care as some of these handlers actually
do important things lib-side
"""


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
        ctx.channel.is_caching = True
        preparse = ctx.raw.split(" = ")
        parse = preparse[1].split(" :")
        nicks = parse[1].split(" ")
        for nick in nicks:
            ctx.channel.cache.add(pyrc.IRCUser(nick, self.client.chmodemap))
            await asyncio.sleep(0)
    
    async def on_366(self, ctx):
        """
        Default handler for numeric event 366 (END OF NAMES), causes the affected channel to sync its temporary userlist to the permanent userlist
        """
        ctx.channel.sync()
    
    async def on_join(self, ctx):
        """
        Default handler for on_join, handles registering the channel with the client lib for IRCClient.get_channel
        """
        channelstr = ctx.message.lstrip(":")
        channels = channelstr.split(" ")
        for channel in channels:
            await asyncio.sleep(0)
            self.client.channels[pyrc.IRCChannel(channel)] = []

    async def on_ready(self):
        """
        Event handler for on_ready, executes commands that were deferred during registration with the IRCd
        """
        self.client.cmdwait = False
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
