# Base image version, un-pinned so a release does not need a Dockerfile edit.
# The default keeps a plain `docker build` working outside CI.
ARG PYTHON_BASE_VERSION=4.35.0

FROM ghcr.io/ds-wizard/python-base:${PYTHON_BASE_VERSION}-basic AS builder

# .dockerignore excludes .git, so the build context carries no repository and
# uv-dynamic-versioning cannot derive the version from a tag. CI passes the
# version in; without it the build fails loudly rather than shipping 0.0.0.
ARG PACKAGE_VERSION
ENV UV_DYNAMIC_VERSIONING_BYPASS=${PACKAGE_VERSION}

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.12.7 /uv /bin/uv

RUN apk add -u build-base gcc \
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

# project.dependencies is dynamic, so `uv export` must build each member's
# metadata rather than read it, and hatchling validates project.readme while
# doing so. READMEs change rarely, so this layer still caches well.
COPY packages/dsw-command-queue/README.md /app/packages/dsw-command-queue/
COPY packages/dsw-config/README.md /app/packages/dsw-config/
COPY packages/dsw-data-seeder/README.md /app/packages/dsw-data-seeder/
COPY packages/dsw-database/README.md /app/packages/dsw-database/
COPY packages/dsw-document-worker/README.md /app/packages/dsw-document-worker/
COPY packages/dsw-mailer/README.md /app/packages/dsw-mailer/
COPY packages/dsw-models/README.md /app/packages/dsw-models/
COPY packages/dsw-storage/README.md /app/packages/dsw-storage/
COPY packages/dsw-tdk/README.md /app/packages/dsw-tdk/

RUN uv export --locked --no-dev --no-emit-workspace --no-hashes --package dsw-data-seeder -o /app/requirements.txt \
 && python -m pip wheel --no-cache-dir --wheel-dir=/app/wheels -r /app/requirements.txt

# Sources: changes on every commit, so everything below rebuilds each time.
COPY . /app

RUN python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/app/wheels /app/packages/dsw-command-queue \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/app/wheels /app/packages/dsw-config \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/app/wheels /app/packages/dsw-database \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/app/wheels /app/packages/dsw-storage \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/app/wheels /app/packages/dsw-data-seeder


FROM ghcr.io/ds-wizard/python-base:${PYTHON_BASE_VERSION}-basic

ENV APPLICATION_CONFIG_PATH=/app/config/application.yml \
    WORKDIR_PATH=/home/user/data \
    SEEDER_RECIPE=example \
    PATH="/home/user/.local/bin:$PATH"

# Setup non-root user
USER user

# Prepare dirs
WORKDIR /home/user
RUN mkdir -p /home/user/data

# Install Python packages
COPY --from=builder --chown=user:user /app/wheels /home/user/wheels
RUN python -m pip install --break-system-packages --user --no-cache --no-index /home/user/wheels/*  \
 && rm -rf /home/user/wheels

# Run
CMD ["dsw-data-seeder", "run"]
