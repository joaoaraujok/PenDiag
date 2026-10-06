"""
Exportador de relatório em formato HTML autossuficiente e estilizado.
"""

import os
import sys
import re
import jinja2
from pendiag.models import DiagnosticReport
from pendiag.utils import format_bytes, format_seconds, format_speed
from pendiag.exporters.json_exporter import export_to_json_str


def _md_bold(text: str) -> str:
    """Converte markdown simples **negrito** em tags <strong> HTML."""
    if not isinstance(text, str):
        return str(text)
    return re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)


def _get_template_content() -> str:
    """Carrega o template HTML a partir do sistema de arquivos ou pacote empacotado."""
    if hasattr(sys, "_MEIPASS"):
        template_path = os.path.join(sys._MEIPASS, "pendiag", "templates", "report_template.html")
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()

    curr_dir = os.path.dirname(os.path.abspath(__file__))
    tmpl_path = os.path.join(curr_dir, "..", "templates", "report_template.html")
    if os.path.exists(tmpl_path):
        with open(tmpl_path, "r", encoding="utf-8") as f:
            return f.read()

    raise FileNotFoundError("Arquivo report_template.html não encontrado.")


def render_html_report(report: DiagnosticReport) -> str:
    """Renderiza o relatório HTML usando Jinja2."""
    template_str = _get_template_content()
    env = jinja2.Environment(autoescape=True)
    env.filters["md_bold"] = _md_bold

    template = env.from_string(template_str)

    raw_json = export_to_json_str(report)

    return template.render(
        report=report,
        raw_json=raw_json,
        format_bytes=format_bytes,
        format_seconds=format_seconds,
        format_speed=format_speed
    )


def save_html_report(report: DiagnosticReport, output_path: str) -> str:
    """Grava o relatório HTML renderizado no caminho especificado."""
    parent_dir = os.path.dirname(os.path.abspath(output_path))
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    html_content = render_html_report(report)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return os.path.abspath(output_path)
