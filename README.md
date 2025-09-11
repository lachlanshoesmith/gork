# gork

stupid discord bot that regurgitates messages its seen before
uses valkey to store data. note that valkey glide does not support redis >=8.0.

store token in GORK_TOKEN env var. GORK_HOSTS should be an array of the format [(hostname, port), ...].
