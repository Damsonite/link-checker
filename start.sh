#!/usr/bin/env bash
set -e

DIR="$(cd -- "$(dirname -- "$0")" >/dev/null 2>&1 || exit 1; pwd -P)"

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "[ERROR] No se encontró Python en el PATH." >&2
    echo "        Instálalo (https://www.python.org/downloads/) y vuelve a intentarlo." >&2
    exit 127
fi

exec "$PY" "$DIR/run.py" "$@"
