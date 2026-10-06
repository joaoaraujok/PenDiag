"""
Teste de estresse rápido e validação de integridade de escrita/leitura em blocos de disco físico (I/O).
"""

import time
import os
import hashlib
import tempfile
from typing import Optional, Callable
from pendiag.models import DiskBenchmarkResult


def run_disk_block_benchmark(
    target_dir: Optional[str] = None,
    size_mb: int = 32,
    block_size_kb: int = 1024,
    progress_callback: Optional[Callable[[str, float], None]] = None
) -> DiskBenchmarkResult:
    """
    Executa um teste de escrita de blocos em disco forçando persistência com fsync,
    leitura sequencial e conferência de integridade com SHA-256.

    Args:
        target_dir: Diretório onde o arquivo de teste será criado (padrão: diretório temporário do SO).
        size_mb: Tamanho total do arquivo de teste em Megabytes (padrão: 32 MB).
        block_size_kb: Tamanho de cada bloco gravado em Kilobytes (padrão: 1024 KB = 1 MB).
        progress_callback: Função opcional callback(etapa: str, progresso_0_a_1: float).

    Returns:
        DiskBenchmarkResult com velocidades de gravação/leitura e confirmação de integridade.
    """
    total_start = time.perf_counter()
    target_dir = target_dir or tempfile.gettempdir()
    test_filepath = os.path.join(target_dir, f"pendiag_iotest_{os.getpid()}_{int(time.time())}.tmp")

    block_bytes = max(4096, block_size_kb * 1024)
    total_bytes = max(block_bytes, size_mb * 1024 * 1024)
    num_blocks = total_bytes // block_bytes
    actual_size_mb = total_bytes / (1024 * 1024)

    # Bloco com padrão pseudoaleatório para evitar distorção por compressão em disco
    pattern = os.urandom(block_bytes)
    hasher_write = hashlib.sha256()

    write_speed = 0.0
    read_speed = 0.0
    integrity_ok = False
    error_msg = None

    try:
        if progress_callback:
            progress_callback(f"Iniciando escrita em disco ({actual_size_mb:.0f} MB)...", 0.0)

        # 1. Teste de Escrita com fsync
        t_write_start = time.perf_counter()
        with open(test_filepath, "wb") as f:
            for b in range(num_blocks):
                f.write(pattern)
                hasher_write.update(pattern)
                if progress_callback:
                    progress_callback(
                        f"Gravando blocos ({b+1}/{num_blocks})",
                        (b + 1) / (num_blocks * 2)
                    )
            f.flush()
            os.fsync(f.fileno())  # Garante flush para o hardware
        t_write_end = time.perf_counter()
        write_duration = max(0.0001, t_write_end - t_write_start)
        write_speed = round(actual_size_mb / write_duration, 2)

        # 2. Teste de Leitura e Checagem de Hash
        if progress_callback:
            progress_callback("Lendo dados e validando integridade...", 0.5)

        hasher_read = hashlib.sha256()
        t_read_start = time.perf_counter()
        with open(test_filepath, "rb") as f:
            block_idx = 0
            while True:
                chunk = f.read(block_bytes)
                if not chunk:
                    break
                hasher_read.update(chunk)
                block_idx += 1
                if progress_callback:
                    progress_callback(
                        f"Lendo blocos ({block_idx}/{num_blocks})",
                        0.5 + (block_idx / (num_blocks * 2))
                    )
        t_read_end = time.perf_counter()
        read_duration = max(0.0001, t_read_end - t_read_start)
        read_speed = round(actual_size_mb / read_duration, 2)

        integrity_ok = (hasher_write.digest() == hasher_read.digest())
        if not integrity_ok:
            error_msg = "Corrupção de blocos: checksum SHA-256 divergiu entre escrita e leitura."

    except Exception as e:
        error_msg = f"Falha no teste de I/O de disco: {str(e)}"
    finally:
        # Limpeza obrigatória do arquivo de teste
        if os.path.exists(test_filepath):
            try:
                os.remove(test_filepath)
            except Exception:
                pass

    total_duration = round(time.perf_counter() - total_start, 2)

    if progress_callback:
        progress_callback("Teste de bloco de disco concluído!", 1.0)

    return DiskBenchmarkResult(
        target_path=target_dir,
        total_size_mb=int(actual_size_mb),
        block_size_kb=block_size_kb,
        write_speed_mb_s=write_speed,
        read_speed_mb_s=read_speed,
        integrity_verified=integrity_ok,
        duration_seconds=total_duration,
        error_message=error_msg
    )
