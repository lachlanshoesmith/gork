import discord
import sys
import random
import hashlib
from gork.db import Valkey
from gork.words import get_substantial_words, TONES, determine_tone


def content_hash(content: str) -> str:
    """Generate a short hash for message content to use as reverse index key."""
    return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()[:16]

MIN_MESSAGES = 10


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

        # Run startup dedup and index building
        await self.__dedup_and_build_index()

        print(f"gork up. aka {self.user}")

    async def __get_random_message(self, guild_id: int, tone: str | None) -> str:
        guild_messages_key = f"guild:{guild_id}:messages"
        msgs_count = await self.db.scard(guild_messages_key)
        if msgs_count < MIN_MESSAGES:
            return f"gork still listening, learning... check back in min. {MIN_MESSAGES - msgs_count} messages from now lol"
        else:
            if not tone:
                msgs = await self.db.srandmember(guild_messages_key)
            else:
                msgs = await self.db.zrandmember(f"{guild_messages_key}:tone:{tone}")

            msg_id: str = msgs[0].decode("utf-8")
            msg = await self.db.get(f"message:{msg_id}")
            msg = msg.decode("utf-8")
            if not msg:
                msg = await self.__get_random_message(guild_id, tone)
            return msg

    async def __delete_message(self, guild_id: int, message_id: int):
        b = self.db.create_batch()
        msg_prefix = f"message:{message_id}"
        guild_msgs_key = f"guild:{guild_id}:messages"
        content_to_id_key = f"guild:{guild_id}:content_to_id"

        # Get content before deleting to remove from reverse index
        content = await self.db.get(msg_prefix)
        if content:
            content_str = content.decode("utf-8") if isinstance(content, bytes) else str(content)
            c_hash = content_hash(content_str)
            b.hdel(content_to_id_key, [c_hash])

        b.delete(msg_prefix)
        # b.delete(f"{msg_prefix}:reactions")
        b.srem(guild_msgs_key, [str(message_id)])

        for tone in TONES:
            b.zrem(f"{guild_msgs_key}:tone:{tone}", [str(message_id)])

        await self.db.execute_batch(b)

    async def __dedup_and_build_index(self):
        """Remove duplicates and build reverse index on startup."""
        # Use Discord.py self.guilds to discover guilds
        if not self.guilds:
            print("Bot is not in any guilds")
            return

        total_dupes = 0

        for guild in self.guilds:
            guild_id = guild.id
            guild_msgs_key = f"guild:{guild_id}:messages"
            content_to_id_key = f"guild:{guild_id}:content_to_id"

            # Check if this guild has stored messages
            msgs_count = await self.db.scard(guild_msgs_key)
            if msgs_count == 0:
                continue

            # Track this guild for future restarts
            await self.db.sadd("gork:guilds", [str(guild_id)])

            # Get all message IDs
            all_msg_ids = await self.db.smembers(guild_msgs_key)
            if not all_msg_ids:
                continue

            seen_content = {}  # content_hash -> msg_id
            duplicates = []

            for msg_id_raw in all_msg_ids:
                msg_id = msg_id_raw.decode("utf-8") if isinstance(msg_id_raw, bytes) else str(msg_id_raw)
                content = await self.db.get(f"message:{msg_id}")
                if not content:
                    continue

                content_str = content.decode("utf-8") if isinstance(content, bytes) else str(content)
                c_hash = content_hash(content_str)

                if c_hash in seen_content:
                    # Duplicate content!
                    duplicates.append(msg_id)
                else:
                    seen_content[c_hash] = msg_id
                    # Ensure reverse index is populated
                    await self.db.hset(content_to_id_key, c_hash, msg_id)

            # Delete duplicates
            for dup_id in duplicates:
                await self.__delete_message(guild_id, int(dup_id))

            total_dupes += len(duplicates)
            print(f"Guild {guild_id}: removed {len(duplicates)} duplicates, indexed {len(seen_content)} unique messages")

        print(f"Dedup complete: removed {total_dupes} total duplicates across all guilds")

    async def __train(self, guild_id: int, message: str, tone: str, delta=1):
        words = get_substantial_words(message)
        guild_words_tone = f"guild:{guild_id}:words:{tone}"
        b = self.db.create_batch()
        for word in words:
            b.zincrby(guild_words_tone, delta, word)
        await self.db.execute_batch(b)

    async def __store_sendable_message(self, guild_id: int, message: discord.Message):
        guild_id_key = f"guild:{guild_id}:messages"
        msg_id = str(message.id)
        msg_content = message.content.strip()
        tone_prefix = f"{guild_id_key}:tone"
        content_to_id_key = f"guild:{guild_id}:content_to_id"

        # Check if content already exists (dedup check)
        c_hash = content_hash(msg_content)
        existing_id = await self.db.hget(content_to_id_key, c_hash)

        if existing_id is not None:
            # Content already stored, skip this message
            return

        msgs_count = await self.db.scard(guild_id_key)
        if msgs_count >= 500:
            msg_to_del = await self.db.srandmember(guild_id_key)
            await self.__delete_message(guild_id, msg_to_del)

        b = self.db.create_batch()
        b.set(f"message:{message.id}", msg_content)
        b.sadd(guild_id_key, [msg_id])
        b.sadd("gork:guilds", [str(guild_id)])  # Track guild ID

        for tone in TONES:
            b.zadd(f"{tone_prefix}:{tone}", {msg_id: 0})

        # Add to reverse index
        b.hset(content_to_id_key, c_hash, msg_id)

        await self.db.execute_batch(b)

    async def __try_store_message(
        self, guild_id: int, message: discord.Message
    ) -> None:
        if message.content.startswith("."):
            # ignore fmbot commands
            return
        if random.randint(0, 4) == 0:
            # this message can be sent by gork
            await self.__store_sendable_message(guild_id, message)

    def __ensure_permissions(self, channel: discord.TextChannel) -> bool:
        return (
            self.permitted_channels is not None
            and channel.id in self.permitted_channels
        )

    def __ensure_maintenance_guild(self, guild_id: int):
        return self.maintenance_guilds and guild_id in self.maintenance_guilds

    def __strip_mentions(self, message: discord.Message) -> discord.Message:
        message.content = message.content.replace("<@1415548973715820645>", "").strip()
        return message

    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return

        guild_id: int = message.guild.id

        if self.maintenance_mode and not self.__ensure_maintenance_guild(guild_id):
            return
        if not self.__ensure_permissions(message.channel) and not self.maintenance_mode:
            return

        # Handle "Delete this. Now." reply command
        if message.reference and message.reference.message_id:
            if message.content.strip() == "Delete this. Now.":
                # Fetch the message being replied to
                try:
                    replied_to_msg = await message.channel.fetch_message(
                        message.reference.message_id
                    )
                except discord.NotFound:
                    await message.reply("Don't understand")
                    return

                target_content = replied_to_msg.content.strip()
                c_hash = content_hash(target_content)
                content_to_id_key = f"guild:{guild_id}:content_to_id"

                existing_id = await self.db.hget(content_to_id_key, c_hash)

                if existing_id is None:
                    await message.reply("Don't understand")
                else:
                    msg_id = existing_id.decode("utf-8") if isinstance(existing_id, bytes) else str(existing_id)
                    await self.__delete_message(guild_id, int(msg_id))
                    await message.reply("Ok")

                return

        if self.user.mentioned_in(message):
            tone = await determine_tone(guild_id, message.content, self.db)

            message: discord.Message = self.__strip_mentions(message)
            await self.__try_store_message(guild_id, message)
            content = await self.__get_random_message(guild_id, tone)
            await message.channel.send(
                content,
                reference=message,
                allowed_mentions=discord.AllowedMentions(
                    users=False, everyone=False, roles=False, replied_user=True
                ),
            )
        else:
            await self.__try_store_message(guild_id, message)

    async def __handle_reaction(
        self, event: discord.RawReactionActionEvent, delta: int
    ):
        if self.maintenance_mode and not self.__ensure_maintenance_guild(
            event.guild_id
        ):
            return

        channel = self.get_channel(event.channel_id)

        if channel is None:
            channel = await self.fetch_channel(event.channel_id)

        if not self.__ensure_permissions(channel) and not self.maintenance_mode:
            return

        emoji = str(event.emoji)
        tone = next((t for t in TONES if emoji in TONES[t]), None)
        if tone is None:
            return

        message = await channel.fetch_message(event.message_id)

        await self.__train(event.guild_id, message.content, tone, delta)

    async def on_raw_reaction_add(self, event: discord.RawReactionActionEvent):
        await self.__handle_reaction(event, delta=1)

    async def on_raw_reaction_remove(self, event: discord.RawReactionActionEvent):
        await self.__handle_reaction(event, delta=-1)
