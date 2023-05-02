#!/bin/sh

set -e

export DSW_SERVER_IMAGE="${DSW_SERVER_IMAGE:-dswbot/wizard-server:develop}"
export DSW_CLIENT_IMAGE="${DSW_CLIENT_IMAGE:-dswbot/wizard-client:develop}"

docker pull --platform linux/amd64 $DSW_SERVER_IMAGE
docker pull --platform linux/amd64 $DSW_CLIENT_IMAGE

docker-compose up -d
sleep 5
./create-bucket.sh
