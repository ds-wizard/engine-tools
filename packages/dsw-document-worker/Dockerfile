FROM ghcr.io/ds-wizard/python-base:4.34.0-docworker AS builder

ARG TARGETARCH

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.12.7 /uv /bin/uv

RUN apk add -u build-base gcc font-noto-emoji \
 && clean

# Dependency manifests only. This layer is invalidated only when dependencies
# change, so the expensive third-party wheel build below is reused across
# commits. All workspace members are needed: `uv export --locked` validates
# the lockfile against the whole workspace.
COPY pyproject.toml uv.lock /app/
COPY packages/dsw-command-queue/pyproject.toml /app/packages/dsw-command-queue/
COPY packages/dsw-config/pyproject.toml /app/packages/dsw-config/
COPY packages/dsw-data-seeder/pyproject.toml /app/packages/dsw-data-seeder/
COPY packages/dsw-database/pyproject.toml /app/packages/dsw-database/
COPY packages/dsw-document-worker/pyproject.toml /app/packages/dsw-document-worker/
COPY packages/dsw-mailer/pyproject.toml /app/packages/dsw-mailer/
COPY packages/dsw-models/pyproject.toml /app/packages/dsw-models/
COPY packages/dsw-storage/pyproject.toml /app/packages/dsw-storage/
COPY packages/dsw-tdk/pyproject.toml /app/packages/dsw-tdk/

RUN uv export --locked --no-dev --no-emit-workspace --no-hashes --package dsw-document-worker -o /app/requirements.txt \
 && python -m pip wheel --wheel-dir=/app/wheels -r /app/requirements.txt

# Sources: changes on every commit, so everything below rebuilds each time.
COPY . /app

RUN python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-command-queue \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-config \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-database \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-storage \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-document-worker/addons/* \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-document-worker

FROM ghcr.io/ds-wizard/python-base:4.34.0-docworker

ENV APPLICATION_CONFIG_PATH=/app/config/application.yml \
    WORKDIR_PATH=/tmp/docworker \
    PATH="/home/user/.local/bin:$PATH"

# Add fonts
COPY packages/dsw-document-worker/resources/fonts /usr/share/fonts/truetype/custom
RUN fc-cache

# Add Pandoc filters
COPY packages/dsw-document-worker/resources/pandoc/filters /pandoc/filters
RUN fc-cache

# Use non-root user
USER user

# Prepare dirs
WORKDIR /home/user
RUN mkdir -p /home/user/templates
COPY --chown=user:user packages/dsw-document-worker/data /home/user/data

# Install Python packages
COPY --from=builder --chown=user:user /app/wheels /home/user/wheels
RUN python -m pip install --break-system-packages --user --no-cache --no-index /home/user/wheels/*  \
 && rm -rf /home/user/wheels

# Run
CMD ["dsw-document-worker", "run"]
