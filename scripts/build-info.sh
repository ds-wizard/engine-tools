#!/usr/bin/env sh
set -e

# File with build info
BUILD_INFO_FILE=build_info.py

# Create version based on git tag or branch
branch=$(git rev-parse --abbrev-ref HEAD)
commit=$(git rev-parse --short HEAD)
sha=$(git rev-parse HEAD)
version="$branch~$commit"
gittag=$(git tag --points-at HEAD | head -n 1)
if test -n "$gittag"
then
    version="$gittag~$commit"
fi

# Get build timestamp
builtAt=$(date +"%Y-%m-%d %TZ")

# Create build_info.py
cat <<EOF > $BUILD_INFO_FILE
# Generated file
# - do not overwrite
# - do not include in git
from collections import namedtuple

BuildInfo = namedtuple(
    'BuildInfo',
    ['version', 'built_at', 'sha', 'branch', 'tag'],
)

BUILD_INFO = BuildInfo(
    version='$version',
    built_at='$builtAt',
    sha='$sha',
    branch='$branch',
    tag='$gittag',
)
EOF

# Copy to every module of every package under the given package roots
# (default: packages). A package's namespace directory is its name up to the
# first dash: packages/dsw-config/dsw/config/build_info.py.
ROOTS=${*:-packages}
for ROOT in $ROOTS; do
    for PKG in $(ls "$ROOT"); do
        NS="${PKG%%-*}"
        [ -d "$ROOT/$PKG/$NS" ] || continue
        for MODULE in $(ls "$ROOT/$PKG/$NS"); do
            DIR="$ROOT/$PKG/$NS/$MODULE"
            if [ -d "$DIR" ]; then
                cp $BUILD_INFO_FILE "$DIR/$BUILD_INFO_FILE"
            fi
        done
    done
done

# Remove temp
rm -f $BUILD_INFO_FILE
