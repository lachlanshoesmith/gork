import discord
import sys
import random
from gork.db import Valkey


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

    async def delete_message(self, guild_id: int, message_id: int):
        b = self.db.create_batch()
        msg_prefix = f"message:{message_id}"
        guild_prefix = f"guild:{guild_id}"
        b.delete(msg_prefix)
        b.delete(f"{msg_prefix}:reactions")
        b.srem(guild_prefix, message_id)
        # for mood in moods, delete...
        self.db.execute_batch(b)

    async def try_store_message(self, guild_id: int, message: discord.Message) -> None:
        guild_id_key = f"guild:{guild_id}"
        mood_prefix = f"{guild_id_key}:mood"

        msg_content = message.content.strip()
        if random.randint(0, 4) == 0:
            msgs_count = await self.db.scard(guild_id_key)
            if msgs_count >= 500:
                msg_to_del = await self.db.srandmember(guild_id_key)
                self.delete_message(guild_id, msg_to_del)

            b = self.db.create_batch()
            b.add(f"message:{message.id}", msg_content)
            b.sadd(guild_id_key, message.id)
            b.zadd(f"{mood_prefix}:happy", {message.id: 0})
            b.zadd(f"{mood_prefix}:sad", {message.id: 0})
            b.zadd(f"{mood_prefix}:angry", {message.id: 0})
            b.zadd(f"{mood_prefix}:surprised", {message.id: 0})
            b.zadd(f"{mood_prefix}:funny", {message.id: 0})
            await self.db.execute_batch(b)

    def ensure_permissions(self, channel: discord.TextChannel) -> bool:
        return (
            self.permitted_channels is not None
            and channel.id in self.permitted_channels
        )

    def ensure_maintenance_guild(self, guild_id: int):
        return self.maintenance_guilds and guild_id in self.maintenance_guilds

    def strip_mentions(self, message: discord.Message):
        message.content = message.content.replace("<@1415548973715820645>", "").strip()
        return message

    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return

        guild_id: int = message.guild.id
        guild_id_key = f"guild:{guild_id}"

        if self.maintenance_mode and not self.ensure_maintenance_guild(guild_id):
            return

        if self.user.mentioned_in(message):
            message = self.strip_mentions(message)
            if self.ensure_permissions(message.channel) or self.maintenance_mode:
                await self.try_store_message(guild_id, message)
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
