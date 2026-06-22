#!/bin/zsh
set -e
cd "$(dirname "$0")"
if [ ! -x ./.venv/bin/python ]; then
  ./setup.command
fi
./.venv/bin/python -m wordforge.studio
