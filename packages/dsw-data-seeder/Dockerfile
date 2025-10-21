FROM datastewardshipwizard/python-base:4.23.2-basic AS builder

WORKDIR /app

COPY . /app

RUN apk add -u build-base gcc \
 && clean

RUN python -m pip wheel --no-cache-dir --wheel-dir=/app/wheels -r /app/packages/dsw-data-seeder/requirements.txt \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/app/wheels /app/packages/dsw-command-queue \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/app/wheels /app/packages/dsw-config \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/app/wheels /app/packages/dsw-database \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/app/wheels /app/packages/dsw-storage \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/app/wheels /app/packages/dsw-data-seeder


FROM datastewardshipwizard/python-base:4.23.2-basic

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
