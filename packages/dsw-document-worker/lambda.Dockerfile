# Base image version, un-pinned so a release does not need a Dockerfile edit.
# The default keeps a plain `docker build` working outside CI.
ARG PYTHON_BASE_VERSION=4.35.0

# The dsw-* distributions are pure Python - every one of them builds to a
# py3-none-any wheel - so they are built once on the build platform and reused
# by every target platform. Under multi-arch emulation that is the difference
# between one native build and one emulated build per architecture, and almost
# all of the emulated cost is PEP 517 build-environment setup repeated per
# package rather than the build itself.
FROM --platform=$BUILDPLATFORM ghcr.io/ds-wizard/python-base:${PYTHON_BASE_VERSION}-docworker-lambda AS workspace-wheels

ARG PACKAGE_VERSION
ENV UV_DYNAMIC_VERSIONING_BYPASS=${PACKAGE_VERSION}

# Sources only: nothing outside packages/ takes part in building a wheel, so a
# change to the docs or the mirror tooling no longer invalidates this layer.
COPY packages /app/packages

# One pip invocation, not one per package: each still gets its own isolated
# build environment, but pip itself starts once.
RUN python -m pip wheel --no-deps --wheel-dir=/app/wheels \
      /app/packages/dsw-command-queue \
      /app/packages/dsw-config \
      /app/packages/dsw-database \
      /app/packages/dsw-storage \
      /app/packages/dsw-document-worker/addons/* \
      /app/packages/dsw-document-worker


# Third-party wheels. These are architecture-specific, so this stage is built
# once per target platform - but it depends only on the dependency manifests,
# so it is reused across commits.
FROM ghcr.io/ds-wizard/python-base:${PYTHON_BASE_VERSION}-docworker-lambda AS builder

# .dockerignore excludes .git, so the build context carries no repository and
# uv-dynamic-versioning cannot derive the version from a tag. CI passes the
# version in; without it the build fails loudly rather than shipping 0.0.0.
ARG PACKAGE_VERSION
ENV UV_DYNAMIC_VERSIONING_BYPASS=${PACKAGE_VERSION}

COPY --from=ghcr.io/astral-sh/uv:0.12.7 /uv /bin/uv

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

# Install Python dependencies (resolved from uv.lock)
RUN uv --directory /app export --locked --no-dev --no-emit-workspace --no-hashes --package dsw-document-worker -o /app/requirements.txt \
 && python -m pip wheel --wheel-dir=/app/wheels -r /app/requirements.txt


FROM ghcr.io/ds-wizard/python-base:${PYTHON_BASE_VERSION}-docworker-lambda

ARG LAMBDA_TASK_ROOT

ENV APPLICATION_CONFIG_PATH=${LAMBDA_TASK_ROOT}/application.yml \
    WORKDIR_PATH=/tmp/docworker \
    EXPERIMENTAL_PDF_WATERMARK=${LAMBDA_TASK_ROOT}/data/watermark.pdf

# Add fonts
COPY packages/dsw-document-worker/resources/fonts /usr/share/fonts/truetype/custom
RUN fc-cache

## Add Pandoc filters
COPY packages/dsw-document-worker/resources/pandoc/filters /pandoc/filters

WORKDIR ${LAMBDA_TASK_ROOT}

# Prepare dirs
RUN mkdir /tmp/docworker
COPY packages/dsw-document-worker/data ./data

# Copy Python dependencies
COPY --from=builder /app/wheels /tmp/wheels
COPY --from=workspace-wheels /app/wheels /tmp/wheels

# uv rather than pip: this unpacks and byte-compiles the whole dependency set,
# and it runs emulated on every non-native architecture. It is bind-mounted
# rather than copied so nothing of it remains in the image.
RUN --mount=from=ghcr.io/astral-sh/uv:0.12.7,source=/uv,target=/usr/local/bin/uv \
    uv pip install --system --no-cache --no-index --compile-bytecode /tmp/wheels/*  \
 && rm -rf /tmp/wheels

# Copy the Lambda handler
COPY packages/dsw-document-worker/resources/lambda_handler.py ${LAMBDA_TASK_ROOT}

# Pass the name of the function handler as an argument to the runtime
ENTRYPOINT [ "python", "-m", "awslambdaric" ]
CMD [ "lambda_handler.handler" ]
