#!/usr/bin/env sh
set -e

for PKG in $(ls packages); do
    echo "Cleaning $PKG"
    rm -rf "packages/$PKG/build"
    rm -rf "packages/$PKG/env"
    find "packages/$PKG" | grep -E "(.egg-info$)" | xargs rm -rf
    find "packages/$PKG" | grep -E "(/__pycache__$|\.pyc$|\.pyo$)" | xargs rm -rf
done
