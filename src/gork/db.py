import builtins
from collections.abc import Mapping
from typing import cast

from glide import (
    Batch,
    ConditionalChange,
    GlideClient,
    GlideClientConfiguration,
    NodeAddress,
    RangeByIndex,
    RangeByLex,
    RangeByScore,
    TEncodable,
)


class Valkey:
    def __init__(self, hosts: list[tuple[str, int]]):
        addresses = [NodeAddress(host, port) for (host, port) in hosts]
        self.config = GlideClientConfiguration(addresses)
        self.client: GlideClient | None = None

    def ensure_client(self):
        if self.client is None:
            raise RuntimeError(
                "Valkey client has not been instantiated. have you connect()ed?"
            )

    async def connect(self):
        if self.client is None:
            self.client = await GlideClient.create(self.config)

    async def set(self, key: str, val: str, conditional_set: bool = False):
        self.ensure_client()
        assert self.client is not None
        if conditional_set:
            set_result = await self.client.set(
                key, val, ConditionalChange.ONLY_IF_DOES_NOT_EXIST
            )
        else:
            set_result = await self.client.set(key, val)
        return set_result

    async def get_or_set(self, key: str, default_val: str):
        self.ensure_client()
        get = await self.get(key)
        if get is None:
            await self.set(key, default_val)
        return get

    async def lpush(self, key: str, val: list[str] | str):
        self.ensure_client()
        assert self.client is not None
        if not isinstance(val, list):
            val = [val]
        push_result = await self.client.lpush(key, cast(list[TEncodable], val))
        return push_result

    async def rpush(self, key: str, val: list[str] | str):
        self.ensure_client()
        assert self.client is not None
        if not isinstance(val, list):
            val = [val]
        push_result = await self.client.rpush(key, cast(list[TEncodable], val))
        return push_result

    async def ltrim(self, key: str, start: int, end: int):
        self.ensure_client()
        assert self.client is not None
        push_result = await self.client.ltrim(key, start, end)
        return push_result

    async def llen(self, key: str) -> int:
        self.ensure_client()
        assert self.client is not None
        llen = await self.client.llen(key)
        return llen

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        self.ensure_client()
        assert self.client is not None
        vals = await self.client.lrange(key, start, end)
        return [v.decode() for v in vals]

    async def get(self, key) -> bytes | None:
        self.ensure_client()
        assert self.client is not None
        get_result = await self.client.get(key)
        return get_result

    async def sadd(self, key: str, val: list[str] | str):
        self.ensure_client()
        assert self.client is not None
        if not isinstance(val, list):
            val = [val]
        push_result = await self.client.sadd(key, cast(list[TEncodable], val))
        return push_result

    async def scard(self, key: str):
        self.ensure_client()
        assert self.client is not None
        cardinality = await self.client.scard(key)
        return cardinality

    async def spop(self, key: str, count=1):
        self.ensure_client()
        assert self.client is not None
        if count < 1:
            raise ValueError("Cannot pop less than 1 element")
        if count > 1:
            pop_result = await self.client.spop_count(key, count)
        else:
            pop_result = await self.client.spop(key)
        return pop_result

    async def srandmember(self, key: str, count=1):
        self.ensure_client()
        assert self.client is not None
        val = await self.client.srandmember_count(key, count)
        return val

    async def smembers(self, key: str) -> builtins.set[str]:
        self.ensure_client()
        assert self.client is not None
        members = await self.client.smembers(key)
        return {m.decode() for m in members}

    async def hset(self, key: str, field: str, value: str):
        self.ensure_client()
        assert self.client is not None
        await self.client.hset(key, {field: value})

    async def hget(self, key: str, field: str) -> str | None:
        self.ensure_client()
        assert self.client is not None
        val = await self.client.hget(key, field)
        return val.decode() if val is not None else None

    async def hdel(self, key: str, field: str):
        self.ensure_client()
        assert self.client is not None
        await self.client.hdel(key, [field])

    async def delete(self, key: str, *args: str):
        self.ensure_client()
        assert self.client is not None
        keys = [key, *args]
        amount_deleted = await self.client.delete(cast(list[TEncodable], keys))
        return amount_deleted

    def create_batch(self, is_atomic=True) -> Batch:
        self.ensure_client()
        return Batch(is_atomic=is_atomic)

    async def execute_batch(self, batch: Batch, raise_on_error=True):
        self.ensure_client()
        assert self.client is not None
        await self.client.exec(batch, raise_on_error)

    async def zadd(self, key: TEncodable, members_scores: Mapping[TEncodable, float]):
        self.ensure_client()
        assert self.client is not None
        elems_added = await self.client.zadd(key, members_scores)
        return elems_added

    async def zrange(
        self,
        key: TEncodable,
        range_query: RangeByIndex | RangeByLex | RangeByScore,
        reverse: bool = False,
    ):
        self.ensure_client()
        assert self.client is not None
        rnge = await self.client.zrange(key, range_query, reverse)
        return rnge

    async def zscore(self, key: TEncodable, member: TEncodable):
        self.ensure_client()
        assert self.client is not None
        return await self.client.zscore(key, member)

    async def zrandmember(self, key: TEncodable, count=1):
        self.ensure_client()
        assert self.client is not None
        val = await self.client.zrandmember_count(key, count)
        return val
