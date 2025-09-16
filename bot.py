import discord
import sys
import random
from db import Valkey


class Gork(discord.Client):
    def __init__(self, db: Valkey, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = db
        self.permitted_channels = kwargs.get("permitted_channels", None)
        self.maintenance_guilds = kwargs.get("maintenance_guilds", None)
        self.maintenance_mode = kwargs.get("maintenance_mode", 0)

    async def on_ready(self):
        try:
            await self.db.connect()
        except Exception as exc:
            print("Failed to connect to Valkey:", exc, file=sys.stderr)
            sys.exit(1)

        print(f"gork up. aka {self.user}")

    async def get_message(self, guild_id_key: str):
        msgs_count = await self.db.scard(guild_id_key)
        if msgs_count < 100:
            return f"gork still listening, learning... check back in min. {100 - msgs_count} messages from now lol"
        else:
            msgs = await self.db.srandmember(guild_id_key)
            msg: str = msgs[0].decode("utf-8")
            return msg

    async def try_store_message(
        self, guild_id_key: str, message: discord.Message
    ) -> None:
        msg_content = message.content.strip()
        if random.randint(0, 4) == 0:
            msgs_count = await self.db.scard(guild_id_key)
            if msgs_count >= 500:
                await self.db.spop(guild_id_key)
            await self.db.sadd(guild_id_key, msg_content)

    def ensure_permissions(self, channel: discord.TextChannel) -> bool:
        return (
            self.permitted_channels is not None
            and channel.id not in self.permitted_channels
        )

    def ensure_maintenance_guild(self, guild_id: int):
        return self.maintenance_guilds and guild_id in self.maintenance_guilds

    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return

        guild_id: int = message.guild.id
        guild_id_key = f"guild:{guild_id}:messages"

        if self.maintenance_mode and not self.ensure_maintenance_guild(guild_id):
            return

        if self.user.mentioned_in(message):
            if message.type == discord.MessageType.reply:
                if self.ensure_permissions(message.channel) or self.maintenance_mode:
                    await self.try_store_message(guild_id_key, message)

            content = await self.get_message(guild_id_key)
            await message.channel.send(
                content,
                reference=message,
                allowed_mentions=discord.AllowedMentions(
                    users=False, everyone=False, roles=False, replied_user=True
                ),
            )
        else:
            if self.ensure_permissions(message.channel) or self.maintenance_mode:
                await self.try_store_message(guild_id_key, message)
