import discord
import sys
import random
from gork.db import Valkey
from gork.words import get_substantial_words

TONES: dict[str, set[str]] = {
    "happy": {"😀", "😃", "😄", "😁", "🙂", "☺️", "😺"},
    "sad": {"☹️", "😥", "😢", "😭", "🙁", "😦", "😿"},
    "surprising": {"🤯", "😲", "😯", "🙀", "😱", "😯"},
    "amusing": {"😆", "🤣", "😂", "😹", "💀", "😸"},
    "enraging": {"😡", "😠", "🤬", "😾"},
}


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

    async def get_random_message(self, guild_id_key: str):
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
        guild_msgs_key = f"guild:{guild_id}:messages"
        b.delete(msg_prefix)
        # b.delete(f"{msg_prefix}:reactions")
        b.srem(guild_msgs_key, message_id)

        for tone in TONES:
            b.zrem(f"{guild_msgs_key}:tone:{tone}", message_id)

        self.db.execute_batch(b)

    async def train(self, guild_id: int, message: str, tone: str):
        words = get_substantial_words(message)
        guild_words_tone = f"guild:{guild_id}:words:{tone}"
        b = self.db.create_batch()
        for word in words:
            b.zincrby(guild_words_tone, 1, word)
        await self.db.execute_batch(b)

    async def store_sendable_message(self, guild_id: int, message: discord.Message):
        guild_id_key = f"guild:{guild_id}:messages"
        msg_id = str(message.id)
        msg_content = message.content.strip()
        tone_prefix = f"{guild_id_key}:tone"

        msgs_count = await self.db.scard(guild_id_key)
        if msgs_count >= 500:
            msg_to_del = await self.db.srandmember(guild_id_key)
            await self.delete_message(guild_id, msg_to_del)

        b = self.db.create_batch()
        b.set(f"message:{message.id}", msg_content)
        b.sadd(guild_id_key, [msg_id])

        for tone in TONES:
            b.zadd(f"{tone_prefix}:{tone}", {msg_id: 0})

        await self.db.execute_batch(b)

    async def try_store_message(self, guild_id: int, message: discord.Message) -> None:
        if random.randint(0, 4) == 0:
            # this message can be sent by gork
            await self.store_sendable_message(guild_id, message)

    def ensure_permissions(self, channel: discord.TextChannel) -> bool:
        return (
            self.permitted_channels is not None
            and channel.id in self.permitted_channels
        )

    def ensure_maintenance_guild(self, guild_id: int):
        return self.maintenance_guilds and guild_id in self.maintenance_guilds

    def strip_mentions(self, message: discord.Message) -> discord.Message:
        message.content = message.content.replace("<@1415548973715820645>", "").strip()
        return message

    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return

        guild_id: int = message.guild.id
        guild_id_key = f"guild:{guild_id}"

        if self.maintenance_mode and not self.ensure_maintenance_guild(guild_id):
            return
        if not self.ensure_permissions(message.channel) and not self.maintenance_mode:
            return

        if self.user.mentioned_in(message):
            message: discord.Message = self.strip_mentions(message)
            await self.try_store_message(guild_id, message)
            content = await self.get_random_message(guild_id_key)
            await message.channel.send(
                content,
                reference=message,
                allowed_mentions=discord.AllowedMentions(
                    users=False, everyone=False, roles=False, replied_user=True
                ),
            )
        else:
            await self.try_store_message(guild_id, message)

    async def on_raw_reaction_add(self, event: discord.RawReactionActionEvent):
        if self.maintenance_mode and not self.ensure_maintenance_guild(event.guild_id):
            return

        channel = self.get_channel(event.channel_id)

        if channel is None:
            channel = await self.fetch_channel(event.channel_id)

        if not self.ensure_permissions(channel) and not self.maintenance_mode:
            return

        emoji = str(event.emoji)
        tone = next((t for t in TONES if emoji in TONES[t]), None)
        if tone is None:
            return

        message = await channel.fetch_message(event.message_id)

        await self.train(event.guild_id, message.content, tone)
