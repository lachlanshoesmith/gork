import os
import ast

from discord import Intents

from gork.bot import Gork
from gork.db import Valkey


TOKEN: str = os.environ["GORK_TOKEN"]
HOSTS: str = os.environ["GORK_HOSTS"]
PERMITTED_CHANNELS: str | None = os.getenv("GORK_PERMITTED_CHANNELS", default=None)
maintenance_mode: int = int(os.getenv(key="GORK_MAINTENANCE_MODE", default=0))
MAINTENANCE_GUILDS: str | None = os.getenv(key="GORK_MAINTENANCE_GUILDS", default=None)

intents = Intents.default()
intents.message_content = True


def main():
    # TODO: change to proper config...
    hosts_list = ast.literal_eval(HOSTS)
    hosts_list = [(host, int(port)) for (host, port) in hosts_list]
    if PERMITTED_CHANNELS:
        permitted_channels = ast.literal_eval(PERMITTED_CHANNELS)
    else:
        permitted_channels = None
    if MAINTENANCE_GUILDS:
        maintenance_guilds = ast.literal_eval(MAINTENANCE_GUILDS)
    else:
        maintenance_guilds = None

    if maintenance_mode == 1:
        MAINTENANCE_MODE = True
        print("gork is in maintenance mode")
    else:
        MAINTENANCE_MODE = False

    db = Valkey(hosts=hosts_list)

    gork = Gork(
        db,
        permitted_channels=permitted_channels,
        maintenance_guilds=maintenance_guilds,
        maintenance_mode=MAINTENANCE_MODE,
        intents=intents,
    )
    gork.run(TOKEN)
