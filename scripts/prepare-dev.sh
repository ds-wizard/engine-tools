#!/usr/bin/env sh

if [ "$1" == "--clean" ]; then
  echo "Cleanup old venv"
  rm -rf env

  echo "Setup new venv"
  python3 -m venv env
fi

. env/bin/activate

echo "Upgrade base tools"
python -m pip install -U pip setuptools wheel

echo ""
echo "Installing packages"
for PKG in $(ls packages); do
  echo "- $PKG"
  pip install -r packages/$PKG/requirements.txt > /dev/null
  pip install packages/$PKG > /dev/null
done
