#!/usr/bin/env sh

cspell-cli \
    --no-progress \
    --no-summary \
    --config .cspell/cspell.json \
    packages/**/*.py \
    packages/**/*.md \
    packages/**/*.json \
    packages/**/*.toml \
    packages/**/*.yml \
    packages/**/*.yaml

