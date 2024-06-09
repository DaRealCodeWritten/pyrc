import pysasl
import logging
from asyncio import TimeoutError
from typing import List
from base64 import b64decode, b64encode
from pysasl.creds.client import ClientCredentials


logger = logging.getLogger("authhelper")


def creds_to_cmd(attempt):
    return f"AUTHENTICATE {b64encode(attempt.response).decode()}"


async def sasl_authenticate(client, methods, user, pwd):
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


async def ns_authenticate(client, passwd, user=None):
    logger.info("Trying to authenticate using method nickserv")
    await client.send(
        f"PRIVMSG NickServ :IDENTIFY {f'{user} {passwd}' if user is not None else passwd}"
    )
    await client.send("CAP END")
