FROM datastewardshipwizard/python-base:3.10-jammy as builder

ARG TARGETARCH

WORKDIR /app

COPY . /app

RUN python -m pip wheel --no-cache-dir --wheel-dir=/root/wheels -r /app/packages/dsw-document-worker/requirements.txt \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/root/wheels /app/packages/dsw-command-queue \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/root/wheels /app/packages/dsw-config \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/root/wheels /app/packages/dsw-database \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/root/wheels /app/packages/dsw-storage \
 && python -m pip wheel --no-cache-dir --wheel-dir=/root/wheels /app/packages/dsw-document-worker/addons/* \
 && python -m pip install --no-cache --no-index /root/wheels/* \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/root/wheels /app/packages/dsw-document-worker

FROM datastewardshipwizard/python-base:3.10-jammy-apt

ARG TARGETARCH
ENV DOCWORKER_CONFIG /app/config.yml
ENV DOCWORKER_WORKDIR /tmp/docworker

WORKDIR /app

RUN mkdir /tmp/docworker && mkdir -p /app/templates

RUN wget --quiet https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.jammy_${TARGETARCH}.deb \
 && apt-get -qy install ./wkhtmltox_0.12.6.1-2.jammy_${TARGETARCH}.deb \
 && wget --quiet https://github.com/jgm/pandoc/releases/download/2.14.1/pandoc-2.14.1-1-${TARGETARCH}.deb \
 && apt-get -qy install ./pandoc-2.14.1-1-${TARGETARCH}.deb \
 && rm -f pandoc-2.14.1-1-${TARGETARCH}.deb wkhtmltox_0.12.6-1.buster_${TARGETARCH}.deb \
 && rm -rf /var/lib/apt/lists/*

COPY packages/dsw-document-worker/fonts /usr/share/fonts/truetype/custom
RUN fc-cache

COPY packages/dsw-document-worker/data /app/data

COPY --from=builder /root/wheels /root/wheels
RUN python -m pip install --no-cache --no-index /root/wheels/*

CMD ["dsw-document-worker"]
