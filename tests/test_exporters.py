"""
Testes unitários para exportação de JSON e HTML.
"""

import unittest
import os
import tempfile
import json
from pendiag.models import DiagnosticReport
from pendiag.collectors.system import collect_system_info
from pendiag.exporters.json_exporter import export_to_json_str, save_json_report
from pendiag.exporters.html_exporter import render_html_report, save_html_report


class TestExporters(unittest.TestCase):

    def setUp(self):
        self.report = DiagnosticReport()
        self.report.system = collect_system_info()

    def test_json_export(self):
        json_str = export_to_json_str(self.report)
        self.assertIsInstance(json_str, str)
        data = json.loads(json_str)
        self.assertEqual(data["version"], "1.0.0")
        self.assertIn("system", data)

    def test_json_save_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "test_rep.json")
            saved_path = save_json_report(self.report, out_file)
            self.assertTrue(os.path.exists(saved_path))
            with open(saved_path, "r", encoding="utf-8") as f:
                d = json.load(f)
                self.assertEqual(d["id"], self.report.id)

    def test_html_render_and_save(self):
        html_str = render_html_report(self.report)
        self.assertIn("<!DOCTYPE html>", html_str)
        self.assertIn("PenDiag", html_str)
        self.assertIn(self.report.system.hostname, html_str)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "test_rep.html")
            saved_path = save_html_report(self.report, out_file)
            self.assertTrue(os.path.exists(saved_path))
            self.assertGreater(os.path.getsize(saved_path), 1000)


if __name__ == "__main__":
    unittest.main()
