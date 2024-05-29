# How to set up IRCClient for the first time
Setting up an IRC client is fairly simple
```py
import pyrc
import asyncio

client = pyrc.IRCClient()

async def main():
    client.connect(...)

asyncio.run(main())
``` 
This is a fairly basic program that won't really do anything, but it provides a good starting point for later work!

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
Events like `on_ready` will not receive any args, nor should they expect any. Other events (such as PRIVMSG, NOTICE, etc) will receive a Context object describing the event context