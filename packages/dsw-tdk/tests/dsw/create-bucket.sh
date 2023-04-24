#!/bin/sh

MINIO_NET="dsw_default"
MINIO_BUCKET="dsw"
MINIO_USER="minio"
MINIO_PASS="minioPassword"

docker run --rm --net $MINIO_NET \
  -e MINIO_BUCKET=$MINIO_BUCKET \
  -e MINIO_USER=$MINIO_USER \
  -e MINIO_PASS=$MINIO_PASS \
  --entrypoint sh minio/mc -c "\
  mc config host add dswminio http://minio:9000 minio minioPassword && \
  mc mb dswminio/\$MINIO_BUCKET
"
