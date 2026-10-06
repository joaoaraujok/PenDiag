@echo off
chcp 65001 >nul
title PenDiag - Diagnóstico Rápido de Hardware e Rede

echo ========================================================
echo   ⚡ PenDiag - Inicializador Portátil de Diagnóstico
echo ========================================================
echo.

set "SCRIPT_DIR=%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

:: 1. Verifica se existe o executável compilado standalone
if exist "%SCRIPT_DIR%dist\pendiag.exe" (
    echo Iniciando PenDiag (Modo Executável Compilado)...
    "%SCRIPT_DIR%dist\pendiag.exe" all --open-browser %*
    goto :END
)

if exist "%SCRIPT_DIR%pendiag.exe" (
    echo Iniciando PenDiag (Modo Executável Direto)...
    "%SCRIPT_DIR%pendiag.exe" all --open-browser %*
    goto :END
)

:: 2. Verifica se há interpretador Python portátil na pasta tools\python do pendrive
if exist "%SCRIPT_DIR%tools\python\python.exe" (
    echo Usando Python Portátil do Pendrive...
    "%SCRIPT_DIR%tools\python\python.exe" "%SCRIPT_DIR%main.py" all --open-browser %*
    goto :END
)

:: 3. Verifica Python instalado no Windows cliente
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python "%SCRIPT_DIR%main.py" all --open-browser %*
    goto :END
)

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    py "%SCRIPT_DIR%main.py" all --open-browser %*
    goto :END
)

echo [ERRO] Nem o executável compilado (pendiag.exe) nem o Python foram encontrados.
echo Para compilar o executavel standalone, execute: python build_exe.py
echo.

:END
echo.
echo ========================================================
echo Diagnóstico finalizado. Pressione qualquer tecla para sair.
echo ========================================================
pause >nul
