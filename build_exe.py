"""
Script de compilação automatizada com PyInstaller para gerar o executável portátil.
Cria um único arquivo binário auto-contido (.exe no Windows, binário no Linux)
que roda direto do pendrive sem precisar de Python instalado na máquina cliente.
"""

import os
import sys

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

import subprocess
import shutil

def build_portable_binary():
    print("=" * 60)
    print("⚡ PenDiag - Compilador de Executável Portátil para Pendrive")
    print("=" * 60)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(base_dir, "main.py")
    templates_dir = os.path.join(base_dir, "pendiag", "templates")

    sep = ";" if sys.platform == "win32" else ":"
    add_data_arg = f"{templates_dir}{sep}pendiag/templates"

    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=pendiag",
        "--onefile",
        "--clean",
        "--noconfirm",
        f"--add-data={add_data_arg}",
        "--hidden-import=jinja2",
        "--hidden-import=psutil",
        "--hidden-import=rich",
        "--hidden-import=typer",
        "--hidden-import=click",
        main_script
    ]

    print(f"Executando compilação PyInstaller...")
    proc = subprocess.run(pyinstaller_cmd, cwd=base_dir)

    if proc.returncode == 0:
        exe_name = "pendiag.exe" if sys.platform == "win32" else "pendiag"
        output_path = os.path.join(base_dir, "dist", exe_name)
        print("\n" + "=" * 60)
        print("✓ COMPILAÇÃO CONCLUÍDA COM SUCESSO!")
        print(f"Executável portátil gerado em: {output_path}")
        print("Copie este arquivo para o pendrive para usar em qualquer máquina.")
        print("=" * 60)
    else:
        print("\n✗ Erro na compilação do executável com PyInstaller.")
        sys.exit(proc.returncode)

if __name__ == "__main__":
    build_portable_binary()
