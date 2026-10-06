#!/usr/bin/env bash
# PenDiag - Inicializador Portátil para Linux / macOS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================================"
echo "  ⚡ PenDiag - Inicializador Portátil de Diagnóstico"
echo "========================================================"

if [ -f "$SCRIPT_DIR/dist/pendiag" ]; then
    "$SCRIPT_DIR/dist/pendiag" all "$@"
elif [ -f "$SCRIPT_DIR/pendiag" ]; then
    "$SCRIPT_DIR/pendiag" all "$@"
elif command -v python3 >/dev/null 2>&1; then
    python3 "$SCRIPT_DIR/main.py" all "$@"
elif command -v python >/dev/null 2>&1; then
    python "$SCRIPT_DIR/main.py" all "$@"
else
    echo "[ERRO] Python ou executável pendiag não encontrado."
    exit 1
fi
