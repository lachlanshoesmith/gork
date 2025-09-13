import discord
import sys
import random
from db import Valkey


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
            return f"gork still listening, learning... check back in min. {100 - msgs_count} messages from now lol"
        else:
            msg_i = random.randint(0, msgs_count - 1)
            msgs = await self.db.lrange(guild_id, msg_i, msg_i)
            msg: str = msgs[0].decode("utf-8")
            print(msg)
            return msg

    async def try_store_message(self, guild_id: str, message: discord.Message) -> None:
        await self.db.lpush(guild_id, message.content)
        await self.db.ltrim(guild_id, 0, 299)

    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return

        guild_id = str(message.guild.id)

        if self.user.mentioned_in(message):
            content = await self.get_message(guild_id)
            await message.channel.send(content, reference=message)
        else:
            await self.try_store_message(guild_id, message)
