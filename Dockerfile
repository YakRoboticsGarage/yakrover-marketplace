FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY . .

RUN uv sync --extra all --no-dev

# Run as non-root user
RUN useradd -r -m -u 1001 appuser && chown -R appuser /app
USER appuser

EXPOSE 8001

CMD ["uv", "run", "python", "mcp_server.py", "--port", "8001", "--host", "0.0.0.0"]
