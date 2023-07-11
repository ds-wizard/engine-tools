FROM datastewardshipwizard/python-base:3.11-alpine-docworker as builder

ARG TARGETARCH

WORKDIR /app

COPY . /app

RUN apk add -u build-base gcc \
 && clean

RUN python -m pip wheel --wheel-dir=/app/wheels -r /app/packages/dsw-document-worker/requirements.txt \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-command-queue \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-config \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-database \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-storage \
 && python -m pip wheel --wheel-dir=/app/wheels /app/packages/dsw-document-worker/addons/* \
 && python -m pip install --no-index /app/wheels/* \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-document-worker

FROM datastewardshipwizard/python-base:3.11-alpine-docworker

ENV APPLICATION_CONFIG_PATH /app/config/application.yml
ENV WORKDIR_PATH /tmp/docworker
ENV PATH "/home/user/.local/bin:$PATH"

# Add fonts and data
COPY packages/dsw-document-worker/fonts /usr/share/fonts/truetype/custom
RUN fc-cache

# Use non-root user
USER user

# Prepare dirs
WORKDIR /home/user
RUN mkdir /tmp/docworker && mkdir -p /home/user/templates
COPY --chown=user:user packages/dsw-document-worker/data /home/user/data

# Install Python packages
COPY --from=builder --chown=user:user /app/wheels /home/user/wheels
RUN python -m pip install --user --no-cache --no-index /home/user/wheels/*  \
 && rm -rf /home/user/wheels

# Run
CMD ["dsw-document-worker"]
