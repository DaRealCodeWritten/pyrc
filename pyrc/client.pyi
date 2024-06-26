from .classes import IRCChannel, IRCUser, Context
from .ext.extension import Extension

class IRCClient:
    async def parse(self, message: str) -> tuple[str, None | Context]: ...
    def add_module(self, module: Extension) -> None: ...
    async def remove_module(self, module_name: str) -> None: ...
    async def register_caps(self, caps: list[str]) -> None: ...
