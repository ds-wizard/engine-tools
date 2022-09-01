FROM datastewardshipwizard/python-base:3.10-jammy as builder

WORKDIR /app

COPY . /app

RUN python -m pip wheel --no-cache-dir --wheel-dir=/root/wheels -r /app/packages/dsw-data-seeder/requirements.txt \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/root/wheels /app/packages/dsw-command-queue \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/root/wheels /app/packages/dsw-config \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/root/wheels /app/packages/dsw-database \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/root/wheels /app/packages/dsw-storage \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/root/wheels /app/packages/dsw-data-seeder


FROM datastewardshipwizard/python-base:3.10-jammy

ENV DSW_CONFIG /app/config.yml
ENV SEEDER_WORKDIR /app/data
ENV SEEDER_RECIPE example

WORKDIR /app

RUN mkdir -p /app/data

COPY --from=builder /root/wheels /root/wheels
RUN python -m pip install --no-cache --no-index /root/wheels/*

CMD ["dsw-data-seeder", "run"]
