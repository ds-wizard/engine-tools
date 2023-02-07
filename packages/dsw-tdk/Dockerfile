FROM datastewardshipwizard/python-base:3.11-jammy as builder

WORKDIR /app

COPY . /app

RUN python -m pip wheel --no-cache-dir --wheel-dir=/root/wheels -r /app/packages/dsw-tdk/requirements.txt \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/root/wheels /app/packages/dsw-tdk


FROM datastewardshipwizard/python-base:3.11-jammy

WORKDIR /app

COPY --from=builder /root/wheels /root/wheels
RUN python -m pip install --no-cache --no-index /root/wheels/*

ENTRYPOINT ["dsw-tdk"]
