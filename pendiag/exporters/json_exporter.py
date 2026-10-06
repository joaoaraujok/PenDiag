"""
Exportador de relatório em formato JSON estruturado.
"""

import os
import json
from pendiag.models import DiagnosticReport


def export_to_json_str(report: DiagnosticReport) -> str:
    """Serializa o relatório completo para uma string JSON com indentação legível."""
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)


def save_json_report(report: DiagnosticReport, output_path: str) -> str:
    """
    Grava o relatório em arquivo JSON no caminho informado.
    Cria os diretórios pais automaticamente se necessário.
    """
    parent_dir = os.path.dirname(os.path.abspath(output_path))
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    json_content = export_to_json_str(report)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(json_content)

    return os.path.abspath(output_path)
