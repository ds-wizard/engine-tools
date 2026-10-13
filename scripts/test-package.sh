#!/bin/sh
# Run verify+test for a single package. The exit code is the only failure
# signal: the caller uses the step outcome recorded by the runner, so this
# must exit non-zero whenever anything failed.
set -u

PKG="$1"

# The package may live under any packages*/ root.
DIR=""
for CANDIDATE in packages*/"$PKG"; do
  if [ -d "$CANDIDATE" ]; then
    DIR="$CANDIDATE"
    break
  fi
done

if [ -z "$DIR" ] || ! cd "$DIR"; then
  echo "## Setup ($PKG): failed - no such package directory"
  exit 1
fi

RET=0

if make verify; then
  echo "## Verify ($PKG): passed"
else
  echo "## Verify ($PKG): failed"
  RET=1
fi

if make test; then
  echo "## Test ($PKG): passed"
else
  echo "## Test ($PKG): failed"
  RET=1
fi

exit $RET
