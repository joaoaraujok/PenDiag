#!/usr/bin/env python3
"""
PenDiag - CLI de Diagnóstico Rápido de Hardware e Rede em Pendrive
Ponto de entrada de execução direta.
"""

import sys
import os

os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from pendiag.cli import main

if __name__ == "__main__":
    main()
