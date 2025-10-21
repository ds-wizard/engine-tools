FROM datastewardshipwizard/python-base:4.23.2-basic AS builder

WORKDIR /app

COPY . /app

RUN python -m pip wheel --no-cache-dir --wheel-dir=/app/wheels -r /app/packages/dsw-tdk/requirements.txt \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/app/wheels /app/packages/dsw-tdk


FROM datastewardshipwizard/python-base:4.23.2-basic

ENV PATH="/home/user/.local/bin:$PATH"

# Setup non-root user
USER user

# Prepare dirs
WORKDIR /home/user

# Install Python packages
COPY --from=builder --chown=user:user /app/wheels /home/user/wheels
RUN python -m pip install --break-system-packages --user --no-cache --no-index /home/user/wheels/*  \
 && rm -rf /home/user/wheels

# Run
ENTRYPOINT ["dsw-tdk"]
