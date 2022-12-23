FROM datastewardshipwizard/python-base:3.11-jammy as builder

WORKDIR /app

COPY . /app

RUN python -m pip wheel --no-cache-dir --wheel-dir=/root/wheels -r /app/packages/dsw-mailer/requirements.txt \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/root/wheels /app/packages/dsw-config \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/root/wheels /app/packages/dsw-command-queue \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/root/wheels /app/packages/dsw-database \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/root/wheels /app/packages/dsw-mailer

FROM datastewardshipwizard/python-base:3.11-jammy

ENV DSW_CONFIG /app/config.yml
ENV MAILER_WORKDIR /app/templates
ENV MAILER_MODE wizard

WORKDIR /app

RUN mkdir -p /tmp/mailer

COPY packages/dsw-mailer/templates /app/templates

COPY --from=builder /root/wheels /root/wheels
RUN python -m pip install --no-cache --no-index /root/wheels/*

CMD ["dsw-mailer", "run"]
