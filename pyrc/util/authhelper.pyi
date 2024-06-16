from typing import List
from pysasl.mechanism import ChallengeResponse
from ..client import IRCClient

def creds_to_cmd(attempt: ChallengeResponse) -> str: ...
async def sasl_authenticate(
    client: IRCClient, methods: List[bytes], user: str, passwd: str
) -> None: ...
async def ns_authenticate(client: IRCClient, pwd: str, user: str = ...) -> None: ...
