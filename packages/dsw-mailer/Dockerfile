FROM datastewardshipwizard/python-base:4.19.2-basic AS builder

WORKDIR /app

COPY . /app

RUN python -m pip wheel --no-cache-dir --wheel-dir=/app/wheels -r /app/packages/dsw-mailer/requirements.txt \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/app/wheels /app/packages/dsw-config \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/app/wheels /app/packages/dsw-command-queue \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/app/wheels /app/packages/dsw-database \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/app/wheels /app/packages/dsw-storage \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/app/wheels /app/packages/dsw-mailer

FROM datastewardshipwizard/python-base:4.19.2-basic

ENV APPLICATION_CONFIG_PATH=/app/config/application.yml \
    WORKDIR_PATH=/home/user/templates \
    PATH="/home/user/.local/bin:$PATH"

# Setup non-root user
USER user

# Prepare dirs
WORKDIR /home/user
RUN mkdir -p /tmp/mailer

# Add templates
COPY --chown=user:user packages/dsw-mailer/templates /home/user/templates

# Install Python packages
COPY --from=builder --chown=user:user /app/wheels /home/user/wheels
RUN python -m pip install --break-system-packages --user --no-cache --no-index /home/user/wheels/*  \
 && rm -rf /home/user/wheels

# Run
CMD ["dsw-mailer", "run"]
