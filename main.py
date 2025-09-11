import discord
import os
import sys
import random
import ast
from db import Valkey

TOKEN: str | None = os.environ["GORK_TOKEN"]
HOSTS: str | None = os.environ["GORK_HOSTS"]

intents = discord.Intents.default()
intents.message_content = True


class Gork(discord.Client):
    def __init__(self, db: Valkey, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = db

    async def on_ready(self):
        try:
            await self.db.connect()
        except Exception as exc:
            print("Failed to connect to Valkey:", exc, file=sys.stderr)
            sys.exit(1)

        print(f"gork up. aka {self.user}")

    async def get_message(self, guild_id: str):
        msgs_count = await self.db.llen(guild_id)
        if msgs_count < 100:
            return "gork still listening, learning..."
        else:
            msg_i = random.randint(0, msgs_count - 1)
            msgs = await self.db.lrange(guild_id, msg_i, msg_i)
            msg: str = msgs[0].decode("utf-8")
            print(msg)
            return msg

    async def try_store_message(self, guild_id: str, message: discord.Message) -> None:
        if random.randint(0, 4) != 0:
            await self.db.rpush(guild_id, message.content)
            await self.db.ltrim(guild_id, 0, 300)

    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return

        guild_id = str(message.guild.id)

        if self.user.mentioned_in(message):
            content = await self.get_message(guild_id)
            await message.channel.send(content, reference=message)
        else:
            await self.try_store_message(guild_id, message)


def main():
    # TODO: change to proper config...
    if HOSTS is None:
        print("Error: HOSTS environment variable not specified.", file=sys.stderr)
        sys.exit(1)
    assert HOSTS is not None

    hosts_list = ast.literal_eval(HOSTS)
    hosts_list = [(host, int(port)) for (host, port) in hosts_list]

    db = Valkey(hosts=hosts_list)

    gork = Gork(db, intents=intents)

    if TOKEN is None:
        print("Error: GORK_TOKEN environment variable not specified.", file=sys.stderr)
        sys.exit(1)
    assert TOKEN is not None

    gork.run(TOKEN)


if __name__ == "__main__":
    main()
