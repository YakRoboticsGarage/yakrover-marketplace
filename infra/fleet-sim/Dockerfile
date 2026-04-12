FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

COPY server.py .

RUN useradd -r -m -u 1001 appuser
USER appuser

EXPOSE 8000
CMD ["python", "server.py"]
