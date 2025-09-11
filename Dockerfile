FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY . /app
RUN uv install
# env vars set in docker compose
CMD ["uv", "run", "main.py"]
