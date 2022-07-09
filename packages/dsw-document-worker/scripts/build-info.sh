#!/bin/bash
set -e

# File with build info
BUILD_INFO_FILE=document_worker/consts.py

# Create version based on git tag or branch
branch=$(git rev-parse --abbrev-ref HEAD)
commit=$(git rev-parse --short HEAD)
version="$branch~$commit"
gittag=$(git tag -l --contains HEAD | head -n 1)
if test -n "$gittag"
then
    version="$gittag~$commit"
fi

# Get build timestamp
builtAt=$(date +"%Y-%m-%d %TZ")

cat $BUILD_INFO_FILE
# Replace values
sed -i.bak "s#--BUILT_AT--#$version#" $BUILD_INFO_FILE && rm $BUILD_INFO_FILE".bak"
sed -i.bak "s#--VERSION--#$builtAt#" $BUILD_INFO_FILE && rm $BUILD_INFO_FILE".bak"

cat $BUILD_INFO_FILE
