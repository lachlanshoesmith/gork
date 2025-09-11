from glide import GlideClient, GlideClientConfiguration, NodeAddress

class Valkey:
    def __init__(self, hosts: list[tuple[str, int]]):
        addresses = [NodeAddress(host, port) for (host, port) in hosts]
        self.config = GlideClientConfiguration(addresses)
        self.client: GlideClient | None = None

    def ensure_client(self):
        if self.client is None:
            raise RuntimeError("Valkey client has not been instantiated. have you connect()ed?") 

    async def connect(self):
        if self.client is None:
            self.client = await GlideClient.create(self.config)
            print('Valkey client connected: ' + self.client)

    async def set(self, key, val):
        self.ensure_client()
        set_result = await self.client.set(key, val)
        print(set_result)

    async def get(self, key):
        self.ensure_client()
        get_result = await self.client.get(key)
        print(get_result)
