#!/bin/sh

cd packages/$1
if make verify; then
  echo "## Verify: passed"
else
  echo "## Verify: failed"
  echo "VERIFY_FAILS=$1:$VERIFY_FAILS" >> $GITHUB_ENV
fi
if make test; then
  echo "## Test: passed"
else
  echo "## Test: failed"
  echo "TEST_FAILS=$1:$TEST_FAILS" >> $GITHUB_ENV
fi
