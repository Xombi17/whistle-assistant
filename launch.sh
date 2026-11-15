#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
exec "$DIR/.venv/bin/python" -u "$DIR/jarvis/app.py" "$@" > /tmp/whistle.log 2>&1
