from glide import GlideClient, GlideClientConfiguration, NodeAddress


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

    async def set(self, key: str, val: str):
        self.ensure_client()
        set_result = await self.client.set(key, val)
        print(set_result)

    async def lpush(self, key: str, val: list[str] | str):
        self.ensure_client()
        if not isinstance(val, list):
            val = [val]
        push_result = await self.client.lpush(key, val)
        print(push_result)

    async def rpush(self, key: str, val: list[str] | str):
        self.ensure_client()
        if not isinstance(val, list):
            val = [val]
        push_result = await self.client.rpush(key, val)
        print(push_result)

    async def ltrim(self, key: str, start: int, end: int):
        self.ensure_client()
        push_result = await self.client.ltrim(key, start, end)
        print(push_result)

    async def llen(self, key: str) -> int:
        self.ensure_client()
        llen = await self.client.llen(key)
        return llen

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        self.ensure_client()
        vals = await self.client.lrange(key, start, end)
        return vals

    async def get(self, key):
        self.ensure_client()
        get_result = await self.client.get(key)
        print(get_result)

    async def sadd(self, key: str, val: list[str] | str):
        self.ensure_client()
        if not isinstance(val, list):
            val = [val]
        push_result = await self.client.sadd(key, val)
        print(push_result)

    async def scard(self, key: str):
        self.ensure_client()
        cardinality = await self.client.scard(key)
        return cardinality

    async def spop(self, key: str, count = 1):
        self.ensure_client()
        pop_result = await self.client.spop(key, count)
        return pop_result

    async def srandmember(self, key: str, count = 1):
        self.ensure_client()
        val = await self.client.srandmember_count(key, count)
        return val
        