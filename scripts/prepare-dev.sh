#!/usr/bin/env sh

echo "Cleanup old venv"
rm -rf env

echo "Setup new venv"
python3 -m venv env
. env/bin/activate

echo "Prepare venv"
python -m pip install -U pip setuptools wheel

echo "Install packages:"
for PKG in $(ls packages); do
  echo "- $PKG"
  pip install -r packages/$PKG/requirements.txt
  pip install packages/$PKG
done
