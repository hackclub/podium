FROM python:3.13

ENV UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y \
    wget
ADD . /app
WORKDIR /app

# Install Doppler CLI
RUN apt-get update && apt-get install -y apt-transport-https ca-certificates curl gnupg && \
    curl -sLf --retry 3 --tlsv1.2 --proto "=https" 'https://packages.doppler.com/public/cli/gpg.DE2A7741A397C129.key' | gpg --dearmor -o /usr/share/keyrings/doppler-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/doppler-archive-keyring.gpg] https://packages.doppler.com/public/cli/deb/debian any-version main" | tee /etc/apt/sources.list.d/doppler-cli.list && \
    apt-get update && \
    apt-get -y install doppler

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync
ENV PATH="/app/.venv/bin:$PATH"

RUN ["uv", "run", "--", "playwright", "install"]

# Use Doppler to inject runtime secrets at container start. Ensure DOPPLER_TOKEN or an agent is available at runtime.
# (commented since we install doppler-env and that loads the env vars if DOPPLER_TOKEN is set)
# ENTRYPOINT ["doppler", "run", "--"]
ENV DOPPLER_ENV=1
CMD ["uv", "run", "python", "-m", "uvicorn", "podium.main:app", "--host", "0.0.0.0", "--port", "8000"]
EXPOSE 8000

# To debug:
# docker build -t podium .
# Example runtime using Doppler token:
# docker run -e DOPPLER_TOKEN=$DOPPLER_TOKEN --env-file .env -p 8000:8000 podium