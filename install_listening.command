#!/bin/bash
# Install the listening trainer's prerequisites: whisper.cpp (local speech-to-
# text) + the English model. afconvert/afplay already ship with macOS.
cd "$(dirname "$0")" || exit 1

echo "==> Installing whisper.cpp …"
brew install whisper-cpp || { echo "brew install failed"; read -n1 -s -r; exit 1; }

mkdir -p models
if [ ! -f models/ggml-base.en.bin ]; then
  echo "==> Downloading English speech model (~148MB, one time) …"
  curl -L --fail -o models/ggml-base.en.bin \
    https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin \
    || { echo "download failed"; read -n1 -s -r; exit 1; }
fi

echo
echo "✓ Done. Try:"
echo "    ./.venv/bin/python -m wordforge.listening library"
echo "    ./.venv/bin/python -m wordforge.listening dictate 1"
read -n 1 -s -r -p "Press any key to close."
