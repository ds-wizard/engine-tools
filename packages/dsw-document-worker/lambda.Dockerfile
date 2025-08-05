FROM datastewardshipwizard/python-base:4.21.0-docworker-lambda AS builder

COPY . /app

# Install Python dependencies
RUN python -m pip wheel --wheel-dir=/app/wheels -r /app/packages/dsw-document-worker/requirements.txt \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-command-queue \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-config \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-database \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-storage \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-document-worker/addons/* \
 && python -m pip wheel --no-deps --wheel-dir=/app/wheels /app/packages/dsw-document-worker

FROM datastewardshipwizard/python-base:4.21.0-docworker-lambda

ARG LAMBDA_TASK_ROOT

ENV APPLICATION_CONFIG_PATH=${LAMBDA_TASK_ROOT}/application.yml \
    WORKDIR_PATH=/tmp/docworker \
    EXPERIMENTAL_PDF_WATERMARK=${LAMBDA_TASK_ROOT}/data/watermark.pdf

# Add fonts
COPY packages/dsw-document-worker/resources/fonts /usr/share/fonts/truetype/custom
RUN fc-cache

## Add Pandoc filters
COPY packages/dsw-document-worker/resources/pandoc/filters /pandoc/filters

WORKDIR ${LAMBDA_TASK_ROOT}

# Prepare dirs
RUN mkdir /tmp/docworker
COPY packages/dsw-document-worker/data ./data

# Copy Python dependencies
COPY --from=builder /app/wheels /tmp/wheels
RUN python -m pip install --no-cache --no-index /tmp/wheels/*  \
 && rm -rf /tmp/wheels

# Copy the Lambda handler
COPY packages/dsw-document-worker/resources/lambda_handler.py ${LAMBDA_TASK_ROOT}

# Pass the name of the function handler as an argument to the runtime
ENTRYPOINT [ "python", "-m", "awslambdaric" ]
CMD [ "lambda_handler.handler" ]
