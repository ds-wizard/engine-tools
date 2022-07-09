FROM python:3.9-slim-buster as builder

WORKDIR /app

RUN apt-get update \
 && apt-get install -qq -y git gcc libpq-dev \
 && rm -rf /var/lib/apt/lists/* \
 && python -m pip install --no-cache-dir -U pip setuptools wheel

COPY . /app

RUN python -OO -m pip wheel --no-cache-dir --wheel-dir=/root/wheels -r /app/packages/dsw-mailer/requirements.txt \
 && python -m pip install --no-cache --no-index /root/wheels/*

RUN --mount=source=.git,target=.git,type=bind \
    python -OO -m pip wheel --no-cache-dir --no-deps --wheel-dir=/root/wheels /app/packages/dsw-mailer

FROM python:3.9-slim-buster

ENV DSW_CONFIG /app/config.yml
ENV MAILER_WORKDIR /app/templates
ENV MAILER_MODE wizard

WORKDIR /app

RUN mkdir -p /tmp/mailer

RUN apt-get update \
 && apt-get install -qq -y gcc libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY packages/dsw-mailer/templates /app/templates

COPY --from=builder /root/wheels /root/wheels
RUN python -m pip install --no-cache --no-index /root/wheels/*
RUN rm -rf /root/wheels

CMD ["dsw-mailer", "run"]
