FROM datastewardshipwizard/python-base:3.11-jammy as builder

ARG TARGETARCH

WORKDIR /app

COPY . /app

RUN python -m pip wheel --no-cache-dir --wheel-dir=/app/wheels -r /app/packages/dsw-document-worker/requirements.txt \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/app/wheels /app/packages/dsw-command-queue \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/app/wheels /app/packages/dsw-config \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/app/wheels /app/packages/dsw-database \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/app/wheels /app/packages/dsw-storage \
 && python -m pip wheel --no-cache-dir --wheel-dir=/app/wheels /app/packages/dsw-document-worker/addons/* \
 && python -m pip install --no-cache --no-index /app/wheels/* \
 && python -m pip wheel --no-cache-dir --no-deps --wheel-dir=/app/wheels /app/packages/dsw-document-worker

FROM datastewardshipwizard/python-base:3.11-jammy-apt

ARG TARGETARCH
ENV DOCWORKER_CONFIG /app/config.yml
ENV DOCWORKER_WORKDIR /tmp/docworker
ENV PATH "/home/user/.local/bin:$PATH"

# Install wkhtmltopdf + pandoc
RUN wget --quiet https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.jammy_${TARGETARCH}.deb \
 && apt-get -qy install ./wkhtmltox_0.12.6.1-2.jammy_${TARGETARCH}.deb \
 && wget --quiet https://github.com/jgm/pandoc/releases/download/2.19.2/pandoc-2.19.2-1-${TARGETARCH}.deb \
 && apt-get -qy install ./pandoc-2.19.2-1-${TARGETARCH}.deb \
 && rm -rf *.deb /var/lib/apt/lists/*

# Add fonts and data
COPY packages/dsw-document-worker/fonts /usr/share/fonts/truetype/custom
RUN fc-cache

# Setup non-root user
RUN groupadd -r user && useradd -r -m -g user user
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
