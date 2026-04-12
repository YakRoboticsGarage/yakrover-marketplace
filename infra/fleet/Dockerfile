FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Clone the yakrover-8004-mcp repo
RUN git clone https://github.com/YakRoboticsGarage/yakrover-8004-mcp.git /app
WORKDIR /app

# Install all dependencies
RUN uv sync --all-extras --no-dev

EXPOSE 8000

# Start fakerover simulator + robot MCP server
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Run as non-root user
RUN useradd -r -m -u 1001 appuser && chown -R appuser /app
USER appuser

CMD ["/app/start.sh"]
