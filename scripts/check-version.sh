#!/usr/bin/env sh
set -e

CONSTS_FILE=$1
TOML_FILE=$2

CONSTS_VERSION=`cat $CONSTS_FILE | grep "^VERSION =" | sed "s/.*= '\(.*\)'/\1/"`
TOML_VERSION=`cat $TOML_FILE | grep "^version =" | sed 's/.*= "\(.*\)"/\1/'`

if [ "$CONSTS_VERSION" != "$TOML_VERSION" ]; then
  echo "Version mismatch: $CONSTS_VERSION vs $TOML_VERSION"
  exit 1
else
  echo "Version matches: $TOML_VERSION"
  exit 0
fi
