FROM datastewardshipwizard/python-base:3.11-docworker-lambda as builder

COPY . /app

# Install Python dependencies
RUN pip install --no-clean -r /app/packages/dsw-document-worker/requirements.txt \
 && pip install --no-clean --no-deps /app/packages/dsw-command-queue \
 && pip install --no-clean --no-deps /app/packages/dsw-config \
 && pip install --no-clean --no-deps /app/packages/dsw-database \
 && pip install --no-clean --no-deps /app/packages/dsw-storage \
 && pip install --no-clean --no-deps /app/packages/dsw-document-worker/addons/* \
 && pip install --no-clean --no-deps /app/packages/dsw-document-worker

FROM datastewardshipwizard/python-base:3.11-docworker-lambda

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
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/

# Copy the Lambda handler
COPY packages/dsw-document-worker/resources/lambda_handler.py ${LAMBDA_TASK_ROOT}

# Pass the name of the function handler as an argument to the runtime
ENTRYPOINT [ "python", "-m", "awslambdaric" ]
CMD [ "lambda_handler.handler" ]
