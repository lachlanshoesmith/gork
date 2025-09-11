FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY . /app
RUN pip install --no-cache-dir .
# env vars set in docker compose
CMD ["uv", "run", "main.py"]
