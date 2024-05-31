# Setting up an event
pyrc allows for a wide variety of events to be listened to via callbacks
```py
client = IRCClient()

# Using a decorator
@client.event
async def on_ready():
    print("ready!")

# Using the method
async def on_ready():
    print("ready!")
client.event(on_ready)
```
Events like `on_ready` will not receive any args, nor should they expect any. Other events (such as PRIVMSG, NOTICE, etc) will receive a [Context](../reference/classes.md#pyrc.classes.Context) object describing the event context

# Waiting for an event, on-the-fly
Sometimes, you need to wait for an event to occur before processing can continue. To do this, simply use `IRCClient.wait_for`

Here's an example of a client that sends a CTCP then waits for the NOTICE in response
```py
import asyncio
import pyrc


client = pyrc.IRCClient()


async def main():
    await client.connect(...)
    await client.ctcp("Foo", "VERSION")
    resp = await client.wait_for("on_notice", lambda ctx: ctx.message.startswith("\x01"))
    # \x01 is the char that signifies the beginning/end of a CTCP query, which per spec can be present in a normal PRIVMSG or NOTICE message
    print(resp.message)


asyncio.run(main())
```
Do note that `wait_for` requires the event to be prefixed with "on_" else it will not work. This will be patched out in later versions 