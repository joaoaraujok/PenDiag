"""
Testes unitários para os benchmarks de RAM e bloco de disco.
"""

import unittest
from unittest.mock import patch, MagicMock
from pendiag.benchmarks.memory_test import run_memory_benchmark
from pendiag.benchmarks.disk_test import run_disk_block_benchmark


class TestBenchmarks(unittest.TestCase):

    def test_memory_benchmark_quick(self):
        # Teste com 8 MB para agilidade nos testes unitários
        res = run_memory_benchmark(size_mb=8)
        self.assertEqual(res.buffer_size_mb, 8)
        self.assertTrue(res.integrity_verified)
        self.assertGreater(res.write_speed_mb_s, 0.0)
        self.assertGreater(res.read_speed_mb_s, 0.0)
        self.assertIsNone(res.error_message)

    def test_memory_benchmark_auto_adjust_on_low_free_memory(self):
        # Simula um cenário onde a memória livre disponível é de apenas 15 MB
        mock_mem = MagicMock()
        mock_mem.available = 15 * 1024 * 1024  # 15 MB livres

        with patch("psutil.virtual_memory", return_value=mock_mem):
            # Solicita 64 MB em uma máquina com apenas 15 MB livres
            res = run_memory_benchmark(size_mb=64)
            self.assertTrue(res.ram_adjusted)
            self.assertEqual(res.requested_size_mb, 64)
            self.assertLessEqual(res.buffer_size_mb, 8)
            self.assertIsNotNone(res.adjustment_reason)
            self.assertTrue(res.integrity_verified)

    def test_disk_benchmark_quick(self):
        # Teste com 4 MB em blocos de 512 KB
        res = run_disk_block_benchmark(size_mb=4, block_size_kb=512)
        self.assertGreaterEqual(res.total_size_mb, 4)
        self.assertTrue(res.integrity_verified)
        self.assertGreater(res.write_speed_mb_s, 0.0)
        self.assertGreater(res.read_speed_mb_s, 0.0)
        self.assertIsNone(res.error_message)

    def test_benchmark_callbacks(self):
        stages = []
        def callback(msg, prog):
            stages.append((msg, prog))

        res = run_memory_benchmark(size_mb=4, progress_callback=callback)
        self.assertTrue(res.integrity_verified)
        self.assertGreater(len(stages), 0)
        self.assertGreaterEqual(stages[-1][1], 1.0)


if __name__ == "__main__":
    unittest.main()
