FROM python:3.13-slim

ENV UV_LINK_MODE=copy

ADD . /app
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync
ENV PATH="/app/.venv/bin:$PATH"

RUN ["uv", "run", "--", "playwright", "install"]

CMD ["uv", "run", "python", "-m", "uvicorn", "podium.main:app", "--host", "0.0.0.0", "--port", "8000"]
EXPOSE 8000

# To debug:
# docker build -t podium .
# docker run -it --rm --env-file .env -v $(pwd)/.secrets.toml:/app/.secrets.toml -p 7001:8000 podium bash -c "ls"