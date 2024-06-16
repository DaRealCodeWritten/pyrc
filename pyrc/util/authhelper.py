import pysasl
import logging
from asyncio import TimeoutError
from typing import List
from base64 import b64decode, b64encode
from pysasl.creds.client import ClientCredentials


logger = logging.getLogger("authhelper")


def creds_to_cmd(attempt: pysasl.mechanism.ChallengeResponse) -> str:
    """Converts a ChallengeResponse object to an AUTHENTICATE command string

    :param attempt: The ChallengeResponse to convert
    :return: Returns the command string generated from the ChallengeResponse given
    """
    return f"AUTHENTICATE {b64encode(attempt.response).decode()}"


async def sasl_authenticate(client, methods: List[bytes], user: str, pwd: str):
    """Authenticates with the IRCd using the methods outlined in `methods`

    :param client: The IRCClient that is authenticating
    :type client: IRCClient
    :param methods: A list of bytes objects that denote what methods to use (methods like SCRAM are NOT SUPPORTED)
    :param user: The username we are authenticating with
    :param pwd: The password to use when authenticating
    """
    mechanisms: pysasl.SASLAuth = pysasl.SASLAuth.named(methods)
    credentials: ClientCredentials = ClientCredentials(user, pwd)
    for mechanism in mechanisms.client_mechanisms:
        await client.send(f"AUTHENTICATE {mechanism.name.decode()}")
        try:
            await client.wait_for("on_raw", lambda raw: raw == "AUTHENTICATE +", 5)
            logger.info(
                f"Trying to authenticate using method sasl-{mechanism.name.decode()}"
            )
            attempt = mechanism.client_attempt(credentials, [])
            await client.send(creds_to_cmd(attempt))
            await client.wait_for("on_900")
            await client.send("CAP END")
        except TimeoutError:
            logger.error(f"Timed out using auth method sasl-{mechanism.name.decode()}")
            continue


async def ns_authenticate(client, pwd: str, user: str=None):
    """Try authenticating using PRIVMSG NickServ IDENTIFY

    :param client: The IRCClient that is authenticating
    :type client: IRCClient
    :param pwd: A string representing the password we are authenticating with
    :param user: The username we're authenticating with
    """    
    logger.info("Trying to authenticate using method nickserv")
    await client.send(
        f"PRIVMSG NickServ :IDENTIFY {f'{user} {pwd}' if user is not None else pwd}"
    )
    await client.send("CAP END")
