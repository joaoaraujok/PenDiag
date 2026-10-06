"""
Teste de estresse de alto desempenho e validação de integridade em Memória RAM.
Otimizado com pré-alocação em bloco único (bytearray), fatiamento via memoryview
e ajuste preventivo com base na memória livre real do sistema para evitar thrashing e OOM.
"""

import time
import hashlib
import os
from typing import Optional, Callable
import psutil
from pendiag.models import MemoryBenchmarkResult


def run_memory_benchmark(
    size_mb: int = 64,
    progress_callback: Optional[Callable[[str, float], None]] = None
) -> MemoryBenchmarkResult:
    """
    Executa teste de integridade e velocidade de RAM com pré-alocação e memoryview.

    Args:
        size_mb: Tamanho solicitado em Megabytes.
        progress_callback: Função opcional callback(etapa: str, progresso_0_a_1: float).

    Returns:
        MemoryBenchmarkResult com velocidades, integridade SHA-256 e metadados de alocação.
    """
    total_start = time.perf_counter()
    original_size_mb = size_mb
    ram_adjusted = False
    adjustment_reason = None

    # 1. Checagem preventiva de memória RAM livre disponível
    try:
        mem_info = psutil.virtual_memory()
        available_bytes = mem_info.available
        required_safety_bytes = int(size_mb * 1.5 * 1024 * 1024)

        if available_bytes < required_safety_bytes:
            # Redimensiona para no máximo 40% da memória disponível (mínimo 4 MB)
            safe_mb = max(4, int((available_bytes * 0.40) / (1024 * 1024)))
            if safe_mb < size_mb:
                size_mb = safe_mb
                ram_adjusted = True
                avail_mb = available_bytes // (1024 * 1024)
                adjustment_reason = (
                    f"Tamanho do teste ajustado automaticamente de {original_size_mb} MB para {size_mb} MB "
                    f"para garantir estabilidade operacional (RAM livre: {avail_mb} MB)."
                )
    except Exception:
        pass

    chunk_size = 1024 * 1024  # 1 MB por bloco
    total_chunks = max(1, size_mb)
    total_bytes = total_chunks * chunk_size

    # Padrão pseudoaleatório determinístico base para o chunk de teste
    pattern = os.urandom(chunk_size)
    hasher_write = hashlib.sha256()

    if progress_callback:
        progress_callback(f"Pré-alocando buffer de RAM ({size_mb} MB)...", 0.0)

    # 2. Pré-alocação segura de buffer único
    try:
        buffer = bytearray(total_bytes)
    except (MemoryError, OverflowError):
        return MemoryBenchmarkResult(
            buffer_size_mb=size_mb,
            write_speed_mb_s=0.0,
            read_speed_mb_s=0.0,
            integrity_verified=False,
            duration_seconds=round(time.perf_counter() - total_start, 2),
            error_message="Memória insuficiente para pré-alocar buffer de teste.",
            requested_size_mb=original_size_mb,
            ram_adjusted=ram_adjusted,
            adjustment_reason=adjustment_reason
        )

    mv = memoryview(buffer)

    # 3. Teste de Escrita Sequencial usando memoryview (Zero Reallocations)
    t_write_start = time.perf_counter()
    for i in range(total_chunks):
        start_offset = i * chunk_size
        end_offset = start_offset + chunk_size
        mv[start_offset:end_offset] = pattern
        hasher_write.update(pattern)
        if progress_callback:
            progress_callback(
                f"Gravando RAM ({i+1}/{total_chunks} MB)",
                (i + 1) / (total_chunks * 2)
            )
    t_write_end = time.perf_counter()
    write_duration = max(0.0001, t_write_end - t_write_start)
    write_speed = round(size_mb / write_duration, 2)

    # 4. Teste de Leitura Sequencial e Validação Criptográfica SHA-256
    hasher_read = hashlib.sha256()
    t_read_start = time.perf_counter()
    for i in range(total_chunks):
        start_offset = i * chunk_size
        end_offset = start_offset + chunk_size
        # Slicing de memoryview não gera nova alocação de heap
        hasher_read.update(mv[start_offset:end_offset])
        if progress_callback:
            progress_callback(
                f"Validando integridade ({i+1}/{total_chunks} MB)",
                0.5 + ((i + 1) / (total_chunks * 2))
            )
    t_read_end = time.perf_counter()
    read_duration = max(0.0001, t_read_end - t_read_start)
    read_speed = round(size_mb / read_duration, 2)

    # Libera imediatamente o memoryview e o buffer do heap
    try:
        mv.release()
    except Exception:
        pass
    del mv
    del buffer

    # Conferência exata de integridade dos hashes
    write_digest = hasher_write.digest()
    read_digest = hasher_read.digest()
    integrity_ok = (write_digest == read_digest)

    total_duration = round(time.perf_counter() - total_start, 2)

    if progress_callback:
        progress_callback("Teste de RAM concluído!", 1.0)

    return MemoryBenchmarkResult(
        buffer_size_mb=size_mb,
        write_speed_mb_s=write_speed,
        read_speed_mb_s=read_speed,
        integrity_verified=integrity_ok,
        duration_seconds=total_duration,
        error_message=None if integrity_ok else "Falha de paridade: hash dos dados divergiu na leitura de RAM.",
        requested_size_mb=original_size_mb,
        ram_adjusted=ram_adjusted,
        adjustment_reason=adjustment_reason
    )
