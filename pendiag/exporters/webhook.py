"""
Envio de relatório de diagnóstico via Webhook / Requisição HTTP POST para servidor central.
"""

import urllib.request
import urllib.error
from typing import Tuple
from pendiag.models import DiagnosticReport
from pendiag.exporters.json_exporter import export_to_json_str


def send_report_webhook(report: DiagnosticReport, url: str, timeout: float = 10.0) -> Tuple[bool, str]:
    """
    Transmite o diagnóstico em formato JSON para um servidor de atendimento ou webhook.

    Returns:
        (sucesso: bool, mensagem_ou_erro: str)
    """
    json_bytes = export_to_json_str(report).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=json_bytes,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": f"PenDiag/{report.version} (Session: {report.id})"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            code = response.getcode()
            if 200 <= code < 300:
                return True, f"Relatório enviado com sucesso! HTTP status: {code}"
            return False, f"Servidor retornou status incomum: {code}"
    except urllib.error.HTTPError as e:
        return False, f"Erro HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return False, f"Falha de conexão com o servidor: {e.reason}"
    except Exception as e:
        return False, f"Erro inesperado no envio: {str(e)}"
