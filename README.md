# gork

stupid discord bot that regurgitates messages its seen before
uses valkey to store data. note that valkey glide does not support redis >=8.0.

## dev

1. `docker run --name gork -d -p 6379:6379 valkey/valkey`
2. store token in GORK_TOKEN env var in .env. GORK_HOSTS should be an array of the format [(valkey_hostname, valkey_port), ...].
3. `uv run --env-file .env python main.py`

## prod

i recommend using the provided `docker-compose.yml`, subbing in your env vars, to orchestrate both valkey and gork.
