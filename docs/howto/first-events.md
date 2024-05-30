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