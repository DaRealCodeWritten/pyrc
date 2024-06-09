from typing import List
from pysasl.mechanism import ChallengeResponse
from ..client import IRCClient

def creds_to_cmd(attempt: ChallengeResponse) -> str: ...
async def sasl_authenticate(
    client: IRCClient, methods: List[str], user: str, passwd: str
) -> None: ...
async def ns_authenticate(client: IRCClient, passwd: str, user: str = ...) -> None: ...
