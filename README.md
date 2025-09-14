# gork

stupid discord bot that regurgitates messages its seen before.

uses valkey to store data. note that valkey glide does not support redis >=8.0.

## dev

1. `docker run --name gork -d -p 6379:6379 valkey/valkey`
2. store token in GORK_TOKEN env var in .env. GORK_HOSTS should be an array of the format [(valkey_hostname, valkey_port), ...]. GORK_PERMITTED_CHANNELS is a ['list', 'of', 'permitted channel IDs'] from which it can store messages. gork can still write to any channel - you can disable this through discord perm mgmt.
3. `uv run --env-file .env gork`

## prod

i recommend using the provided `docker-compose.yml`, subbing in your env vars (or using a .env).
this will orchestrate both valkey and gork.
