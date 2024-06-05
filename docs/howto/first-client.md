# How to set up IRCClient for the first time
Setting up an IRC client is fairly simple. see the docs for [IRCClient.connect](../reference/client.md#pyrc.IRCClient.connect) to see what args are required to connect an IRCClient to an IRCd
```py
import pyrc
import asyncio

client = pyrc.IRCClient()

async def main():
    client.connect(...)

asyncio.run(main())
``` 
This is a fairly basic program that won't really do anything, but it provides a good starting point for later work!

# Sending your first message
We've connected to IRC, but now we wanna send messages, so lets do it!
```py
import asyncio
import pyrc

client = pyrc.IRCClient()

async def main():
    await client.connect("127.0.0.1", 6667, "Foo")  # Connect to an IRCd at 127.0.0.1, port 6667, with username 'Foo'
    chan = await client.join_channel("#spam")  # Join the channel '#spam'
    await chan.send_to("Hello, world!")  # Hello, world!

asyncio.run(main())
```
