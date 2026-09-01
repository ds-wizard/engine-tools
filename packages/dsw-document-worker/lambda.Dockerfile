FROM ghcr.io/ds-wizard/python-base:4.34.0-docworker-lambda AS builder

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

# Install Python dependencies (resolved from uv.lock)
RUN uv --directory /app export --locked --no-dev --no-emit-workspace --no-hashes --package dsw-document-worker -o /app/requirements.txt \
 && python -m pip wheel --wheel-dir=/app/wheels -r /app/requirements.txt

# Sources: changes on every commit, so everything below rebuilds each time.
COPY . /app

RUN python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-command-queue \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-config \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-database \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-storage \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-document-worker/addons/* \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-document-worker

FROM ghcr.io/ds-wizard/python-base:4.34.0-docworker-lambda

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
RUN python -m pip install --no-cache --no-index /tmp/wheels/*  \
 && rm -rf /tmp/wheels

# Copy the Lambda handler
COPY packages/dsw-document-worker/resources/lambda_handler.py ${LAMBDA_TASK_ROOT}

# Pass the name of the function handler as an argument to the runtime
ENTRYPOINT [ "python", "-m", "awslambdaric" ]
CMD [ "lambda_handler.handler" ]
