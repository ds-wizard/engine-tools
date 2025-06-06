FROM datastewardshipwizard/python-base:4.19.1-docworker AS builder

ARG TARGETARCH

WORKDIR /app

COPY . /app

RUN apk add -u build-base gcc font-noto-emoji \
 && clean

RUN python -m pip wheel --wheel-dir=/app/wheels -r /app/packages/dsw-document-worker/requirements.txt \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-command-queue \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-config \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-database \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-storage \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-document-worker/addons/* \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-document-worker

FROM datastewardshipwizard/python-base:4.19.1-docworker

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
RUN mkdir /tmp/docworker && mkdir -p /home/user/templates
COPY --chown=user:user packages/dsw-document-worker/data /home/user/data

# Install Python packages
COPY --from=builder --chown=user:user /app/wheels /home/user/wheels
RUN python -m pip install --break-system-packages --user --no-cache --no-index /home/user/wheels/*  \
 && rm -rf /home/user/wheels

# Run
CMD ["dsw-document-worker", "run"]
