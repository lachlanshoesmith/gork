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
        await self.db.connect()

        print(f'gork up. aka {self.user}')

    def try_store_message(message: discord.Message) -> None:
        if random.randint(0,4) != 0:
            return        

    
    async def on_message(self, message: discord.Message):
        if self.user.mentioned_in(message):
            print(f'message from {message.author}: {message.content}')
        else:
            self.try_store_message(message)

def main():
    # TODO: change to proper config...
    hosts_list = ast.literal_eval(HOSTS)
    hosts_list = [(host, int(port)) for (host, port) in hosts_list]


    db = Valkey(hosts=hosts_list)

    gork = Gork(db, intents=intents)

    if TOKEN is None:
        print('Error: GORK_TOKEN environment variable not specified.')
        sys.exit(1)

    gork.run(TOKEN)

if __name__ == "__main__":
    main()

