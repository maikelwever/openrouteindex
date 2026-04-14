FROM python:3.13-slim AS python-base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    UV_COMPILE_BYTECODE=1 \
    PYSETUP_PATH="/app" \
    VENV_PATH="/app/.venv"

# prepend poetry and venv to path
ENV PATH="$VENV_PATH/bin:$PATH"

RUN apt-get update && apt-get install -qy osm2pgsql && apt-get clean

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR $PYSETUP_PATH
COPY . /app/

RUN --mount=type=cache,target=/root/.cache uv sync --locked

ENTRYPOINT ["uv", "run", "ori-updater", "--loop", "--upload"]
