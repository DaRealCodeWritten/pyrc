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