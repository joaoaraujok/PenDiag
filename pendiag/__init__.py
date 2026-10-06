"""
PenDiag - CLI de Diagnóstico Rápido de Hardware e Rede em Pendrive
"""

import sys

# Garante compatibilidade universal com UTF-8 nos terminais Windows
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

__version__ = "1.0.0"
__author__ = "PenDiag Diagnostic Suite"
