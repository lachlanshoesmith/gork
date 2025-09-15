import os
import ast
from bot import Gork
from db import Valkey
from discord import Intents


TOKEN: str = os.environ["GORK_TOKEN"]
HOSTS: str = os.environ["GORK_HOSTS"]
PERMITTED_CHANNELS: str | None = os.getenv("GORK_PERMITTED_CHANNELS", default=None)

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
    db = Valkey(hosts=hosts_list)

    gork = Gork(db, permitted_channels=permitted_channels, intents=intents)
    gork.run(TOKEN)


if __name__ == "__main__":
    main()
