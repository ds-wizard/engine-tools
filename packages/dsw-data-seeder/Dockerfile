FROM python:3.9-slim-buster as builder

WORKDIR /app

RUN apt-get update \
 && apt-get install -qq -y git gcc libpq-dev \
 && rm -rf /var/lib/apt/lists/* \
 && python -m pip install --no-cache-dir -U pip setuptools wheel

COPY . /app

RUN python -m pip wheel --no-cache-dir --wheel-dir=/root/wheels -r /app/packages/dsw-data-seeder/requirements.txt \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/root/wheels /app/packages/dsw-command-queue \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/root/wheels /app/packages/dsw-config \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/root/wheels /app/packages/dsw-database \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/root/wheels /app/packages/dsw-storage \
 && python -m pip install --no-cache --no-index /root/wheels/*

RUN --mount=source=.git,target=.git,type=bind \
    python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/root/wheels /app/packages/dsw-data-seeder


FROM python:3.9-slim-buster

ENV DSW_CONFIG /app/config.yml
ENV SEEDER_WORKDIR /app/data
ENV SEEDER_RECIPE example

WORKDIR /app

RUN mkdir -p /app/data

RUN apt-get update \
 && apt-get install -qq -y gcc libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/wheels /root/wheels
RUN python -m pip install --no-cache --no-index /root/wheels/* \
 && rm -rf /root/wheels

CMD ["dsw-data-seeder", "run"]
