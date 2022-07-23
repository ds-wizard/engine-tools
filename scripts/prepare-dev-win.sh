#!/usr/bin/env sh

echo "Cleanup old venv"
rm -rf env

echo "Setup new venv"
python -m venv env
. env/Scripts/activate

echo "Prepare venv"
python -m pip install -U pip setuptools wheel

echo "Install packages:"
for PKG in $(ls packages); do
  echo "- $PKG"
  pip install -r packages/$PKG/requirements.txt
  pip install packages/$PKG
done
