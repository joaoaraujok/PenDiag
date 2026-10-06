"""
Funções utilitárias de formatação, pontuação de saúde, laudo executivo e detecção de ambiente.
"""

from typing import Tuple, List
import os
import sys
from pendiag.models import DiagnosticReport, DiagnosticAlert


def format_bytes(bytes_value: int) -> str:
    """Formata valor em bytes para representação legível (B, KB, MB, GB, TB)."""
    if bytes_value is None or bytes_value < 0:
        return "N/A"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    value = float(bytes_value)
    unit_index = 0
    while value >= 1024.0 and unit_index < len(units) - 1:
        value /= 1024.0
        unit_index += 1
    return f"{value:.2f} {units[unit_index]}"


def format_seconds(seconds: float) -> str:
    """Converte segundos para formato legível de tempo (ex: 2d 5h 12m 30s)."""
    if seconds is None or seconds < 0:
        return "N/A"
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or hours > 0 or days > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def format_speed(mb_s: float) -> str:
    """Formata velocidade em MB/s ou GB/s."""
    if mb_s is None or mb_s < 0:
        return "N/A"
    if mb_s >= 1024.0:
        return f"{mb_s / 1024.0:.2f} GB/s"
    return f"{mb_s:.2f} MB/s"


def evaluate_health(report: DiagnosticReport) -> Tuple[int, str, List[DiagnosticAlert]]:
    """
    Avalia todas as métricas coletadas e calcula uma pontuação de saúde (0 a 100),
    um status geral (SAUDAVEL, ATENCAO, CRITICO) e uma lista de alertas.
    Elimina falsos positivos de firewalls de roteadores locais quando há conectividade WAN ativa.
    """
    score = 100
    alerts: List[DiagnosticAlert] = []

    # 1. Sistema, Processador & Memória
    if report.system:
        if report.system.ram_usage_percent >= 92.0:
            score -= 15
            alerts.append(DiagnosticAlert(
                level="CRITICAL",
                category="MEMORIA",
                message=f"Uso de memória RAM crítico: {report.system.ram_usage_percent:.1f}%",
                detail="O sistema pode sofrer lentidão severa ou travamentos por falta de memória livre."
            ))
        elif report.system.ram_usage_percent >= 80.0:
            score -= 5
            alerts.append(DiagnosticAlert(
                level="WARNING",
                category="MEMORIA",
                message=f"Uso de memória RAM elevado: {report.system.ram_usage_percent:.1f}%",
                detail="Consumo acima do ideal para operações normais."
            ))

        if report.system.cpu_usage_percent >= 90.0:
            score -= 10
            alerts.append(DiagnosticAlert(
                level="WARNING",
                category="SISTEMA",
                message=f"Uso de CPU momentâneo muito alto: {report.system.cpu_usage_percent:.1f}%"
            ))

        # Temperatura de CPU
        if report.system.cpu_temperature_c and report.system.cpu_temperature_c >= 85.0:
            score -= 10
            alerts.append(DiagnosticAlert(
                level="WARNING",
                category="SISTEMA",
                message=f"Temperatura do processador muito alta: {report.system.cpu_temperature_c:.1f}°C",
                detail="Pode indicar necessidade de limpeza de coolers ou troca de pasta térmica."
            ))

        # Antivírus
        if report.system.antivirus_name and report.system.antivirus_enabled is False:
            score -= 10
            alerts.append(DiagnosticAlert(
                level="WARNING",
                category="SEGURANCA",
                message=f"Proteção antivírus em tempo real desativada ({report.system.antivirus_name}).",
                detail="O equipamento está vulnerável a ameaças e pragas virtuais."
            ))

    # 2. Armazenamento e S.M.A.R.T.
    if report.disk:
        for disk in report.disk.disks:
            health = (disk.health_status or "").lower()
            if health in ["unhealthy", "failing", "bad", "critico", "falha"]:
                score -= 40
                alerts.append(DiagnosticAlert(
                    level="CRITICAL",
                    category="DISCO",
                    message=f"Disco com alerta S.M.A.R.T. crítico: {disk.name} (Status: {disk.health_status})",
                    detail="Risco iminente de perda de dados. Recomenda-se backup imediato e substituição do disco."
                ))
            elif health in ["warning", "degraded", "atencao"]:
                score -= 20
                alerts.append(DiagnosticAlert(
                    level="WARNING",
                    category="DISCO",
                    message=f"Disco com alerta de atenção: {disk.name} (Status: {disk.health_status})",
                    detail="Monitore o disco e providencie cópia de segurança preventiva."
                ))

            if disk.temperature_c and disk.temperature_c >= 65.0:
                alerts.append(DiagnosticAlert(
                    level="WARNING",
                    category="DISCO",
                    message=f"Temperatura da unidade {disk.name} elevada: {disk.temperature_c:.0f}°C",
                    detail="Altas temperaturas reduzem a vida útil e velocidade de leitura de SSDs."
                ))

            if disk.wear_percent and disk.wear_percent >= 80.0:
                score -= 15
                alerts.append(DiagnosticAlert(
                    level="WARNING",
                    category="DISCO",
                    message=f"Desgaste avançado do SSD {disk.name}: {disk.wear_percent:.0f}% de desgaste",
                    detail="O ciclo de vida útil estimado das células de memória flash está próximo do esgotamento."
                ))

        for part in report.disk.partitions:
            if part.usage_percent >= 95.0:
                score -= 15
                alerts.append(DiagnosticAlert(
                    level="CRITICAL",
                    category="DISCO",
                    message=f"Partição {part.mountpoint} quase cheia: {part.usage_percent:.1f}% ocupada",
                    detail=f"Espaço livre crítico ({format_bytes(part.free_bytes)})."
                ))
            elif part.usage_percent >= 88.0:
                score -= 5
                alerts.append(DiagnosticAlert(
                    level="WARNING",
                    category="DISCO",
                    message=f"Partição {part.mountpoint} com pouco espaço: {part.usage_percent:.1f}% ocupada"
                ))

    # 3. Bateria
    if report.battery and report.battery.present:
        wear = report.battery.wear_level_percent
        if wear is not None:
            if wear >= 50.0:
                score -= 15
                alerts.append(DiagnosticAlert(
                    level="CRITICAL",
                    category="BATERIA",
                    message=f"Desgaste severo da bateria: {wear:.1f}% de perda de capacidade nominal",
                    detail="A autonomia do equipamento está substancialmente reduzida."
                ))
            elif wear >= 30.0:
                score -= 8
                alerts.append(DiagnosticAlert(
                    level="WARNING",
                    category="BATERIA",
                    message=f"Desgaste moderado da bateria: {wear:.1f}% de degradação"
                ))

    # 4. Rede
    if report.network:
        if not report.network.internet_connected:
            score -= 20
            alerts.append(DiagnosticAlert(
                level="WARNING",
                category="REDE",
                message="Sem conectividade com a Internet ou gateway inalcançável.",
                detail="Testes de ping e DNS falharam em alcançar a rede externa."
            ))
        else:
            # Internet conectada com sucesso!
            # Trata ping especificamente: ignora perda no Gateway local se o tráfego WAN passou
            gw_ip = report.network.gateway_ip

            for ping in report.network.ping_tests:
                is_gw = (gw_ip and ping.target == gw_ip)
                if is_gw:
                    # Gateway local bloqueou ICMP mas a internet funciona normalmente
                    if ping.packet_loss_percent > 0:
                        alerts.append(DiagnosticAlert(
                            level="INFO",
                            category="REDE",
                            message=f"Roteador/Gateway local ({ping.target}) com ICMP/ping filtrado por firewall.",
                            detail="Comportamento padrão de segurança em roteadores modernos. A navegação WAN opera normalmente."
                        ))
                    continue

                # Alvos de Internet pública (WAN)
                if ping.packet_loss_percent >= 50.0:
                    score -= 10
                    alerts.append(DiagnosticAlert(
                        level="WARNING",
                        category="REDE",
                        message=f"Alta perda de pacotes para {ping.target}: {ping.packet_loss_percent:.1f}%",
                        detail="Pode indicar instabilidade na conexão física, Wi-Fi ou rota de operadora."
                    ))
                elif ping.avg_rtt_ms and ping.avg_rtt_ms > 150.0:
                    score -= 5
                    alerts.append(DiagnosticAlert(
                        level="WARNING",
                        category="REDE",
                        message=f"Latência de rede elevada para {ping.target}: {ping.avg_rtt_ms:.1f} ms"
                    ))

            for dns in report.network.dns_tests:
                if not dns.success:
                    score -= 5
                    alerts.append(DiagnosticAlert(
                        level="WARNING",
                        category="REDE",
                        message=f"Falha na resolução DNS para {dns.domain} ({dns.dns_server})"
                    ))
                elif dns.latency_ms and dns.latency_ms > 120.0:
                    alerts.append(DiagnosticAlert(
                        level="INFO",
                        category="REDE",
                        message=f"Resolução DNS lenta para {dns.domain}: {dns.latency_ms:.1f} ms"
                    ))

    # 5. Benchmarks
    if report.benchmark:
        if report.benchmark.memory_benchmark:
            if not report.benchmark.memory_benchmark.integrity_verified:
                score -= 40
                alerts.append(DiagnosticAlert(
                    level="CRITICAL",
                    category="MEMORIA",
                    message="ERRO DE INTEGRIDADE NA MEMÓRIA RAM DETECTADO!",
                    detail="Padrão de dados gravado na RAM divergiu na leitura. Indício claro de defeito físico nos módulos de memória."
                ))
            if report.benchmark.memory_benchmark.ram_adjusted:
                alerts.append(DiagnosticAlert(
                    level="INFO",
                    category="MEMORIA",
                    message=report.benchmark.memory_benchmark.adjustment_reason or "Tamanho do teste de RAM ajustado para segurança."
                ))

        if report.benchmark.disk_benchmark:
            if not report.benchmark.disk_benchmark.integrity_verified:
                score -= 40
                alerts.append(DiagnosticAlert(
                    level="CRITICAL",
                    category="DISCO",
                    message="ERRO DE INTEGRIDADE NO TESTE DE BLOCO DE DISCO!",
                    detail="Arquivo de teste temporário sofreu corrupção na gravação/leitura com fsync."
                ))

    # Limita o score entre 0 e 100
    score = max(0, min(100, score))

    if score >= 85:
        status = "SAUDAVEL"
    elif score >= 60:
        status = "ATENCAO"
    else:
        status = "CRITICO"

    return score, status, alerts


def generate_executive_summary(report: DiagnosticReport) -> List[str]:
    """
    Gera um parecer técnico e comercial em linguagem clara, objetiva e acessível para clientes leigos.
    """
    summary: List[str] = []

    # 1. Visão Geral do Equipamento
    score = report.health_score
    if score >= 85:
        summary.append(
            "🛡️ **Diagnóstico Geral Positivo:** O equipamento apresenta excelente estabilidade, saúde de hardware e conectividade confiável para as atividades do dia a dia."
        )
    elif score >= 60:
        summary.append(
            "⚠️ **Atenção Técnica Preventiva:** Foram identificados pontos de melhoria que demandam intervenção preventiva para restaurar o desempenho ideal e evitar paradas não planejadas."
        )
    else:
        summary.append(
            "🚨 **Intervenção Urgente Necessária:** O computador possui componentes críticos comprometidos ou operando em nível de risco elevado, necessitando de reparo imediato."
        )

    # 2. Memória RAM
    if report.system:
        ram_pct = report.system.ram_usage_percent
        ram_total_gb = report.system.ram_total_bytes / (1024**3)
        ram_used_gb = report.system.ram_used_bytes / (1024**3)

        if ram_pct >= 90.0:
            summary.append(
                f"⚡ **Memória RAM no Limite ({ram_pct:.0f}% em uso):** O sistema está consumindo quase a totalidade dos {ram_total_gb:.1f} GB instalados ({ram_used_gb:.1f} GB em uso). "
                "**Recomendação Comercial:** Recomenda-se upgrade de memória RAM (adição de novo módulo) para eliminar lentidão e travamentos ao usar múltiplos programas e abas."
            )
        elif ram_pct >= 75.0:
            summary.append(
                f"ℹ️ **Consumo de Memória Elevado ({ram_pct:.0f}%):** A memória está sendo bem aproveitada, mas aproxima-se da capacidade máxima sob carga pesada. Fechar programas em segundo plano mantém a agilidade."
            )
        else:
            summary.append(
                f"✓ **Memória RAM Balanceada:** Capacidade de memória ({ram_total_gb:.1f} GB) suficiente e com folga adequada para a operação normal."
            )

    # 3. Armazenamento e Disco
    if report.disk:
        has_smart_failure = any(not d.is_smart_ok for d in report.disk.disks)
        full_parts = [p for p in report.disk.partitions if p.usage_percent >= 88.0]

        if has_smart_failure:
            summary.append(
                "🚨 **Alerta Crítico no Armazenamento:** A unidade de disco informou desgaste físico ou falha de leitura (S.M.A.R.T.). "
                "**Recomendação Urgente:** Realizar imediatamente o backup completo dos arquivos e providenciar a substituição do disco por um novo SSD."
            )
        elif full_parts:
            parts_str = ", ".join([f"{p.mountpoint} ({p.usage_percent:.0f}%)" for p in full_parts])
            summary.append(
                f"⚠️ **Pouco Espaço em Disco:** As seguintes unidades estão com pouco espaço livre: {parts_str}. "
                "**Recomendação:** Limpeza de arquivos temporários, downloads antigos ou expansão da capacidade de armazenamento."
            )
        else:
            summary.append(
                "✓ **Armazenamento Saudável:** As unidades de disco (SSD/HDD) encontram-se em perfeito estado de funcionamento físico, com 100% de aprovação nos testes de integridade S.M.A.R.T."
            )

    # 4. Bateria
    if report.battery:
        if report.battery.present:
            wear = report.battery.wear_level_percent
            if wear is not None and wear >= 30.0:
                summary.append(
                    f"🔋 **Desgaste Notável da Bateria ({wear:.0f}% de degradação):** A bateria perdeu capacidade comparada a quando era nova de fábrica. "
                    "**Recomendação:** A autonomia longe do carregador está reduzida. Se o equipamento precisar de mobilidade prolongada, planeje a troca da bateria."
                )
            elif wear is not None and wear < 30.0:
                health = 100.0 - wear
                summary.append(
                    f"✓ **Bateria Saudável:** Retém {health:.0f}% da capacidade original de fábrica, operando dentro dos parâmetros esperados."
                )
        else:
            summary.append("ℹ️ **Alimentação Estacionária:** Equipamento alimentado via tomada elétrica contínua (Computador Desktop).")

    # 5. Rede e Internet
    if report.network:
        if report.network.internet_connected:
            dns_fast = all(d.success and (d.latency_ms or 0) < 90 for d in report.network.dns_tests)
            if dns_fast:
                summary.append("✓ **Conexão de Rede Estável:** Acesso à Internet ativo, com resolução de nomes ágil e rotas de comunicação rápidas.")
            else:
                summary.append("ℹ️ **Navegação Funcional:** Acesso à Internet operacional, com tempo de resposta moderado dos servidores de navegação.")
        else:
            summary.append("🚨 **Sem Conectividade com a Internet:** O computador não conseguiu alcançar a rede externa. Verifique cabo de rede, Wi-Fi ou roteador de borda.")

    # 6. Segurança e Antivírus
    if report.system and report.system.antivirus_name:
        if report.system.antivirus_enabled:
            summary.append(f"✓ **Segurança Operacional:** Proteção em tempo real ativa e monitorada por {report.system.antivirus_name}.")
        else:
            summary.append(f"⚠️ **Antivírus Desativado:** O software de segurança {report.system.antivirus_name} encontra-se inativo. Recomenda-se ativar a proteção imediatamente.")

    # 7. Integridade de Dados dos Benchmarks
    if report.benchmark and report.benchmark.memory_benchmark and report.benchmark.disk_benchmark:
        if report.benchmark.memory_benchmark.integrity_verified and report.benchmark.disk_benchmark.integrity_verified:
            summary.append(
                "✓ **Integridade de Dados Aprovada (SHA-256):** Testes de estresse em memória e escrita física em bloco de disco executados sem nenhuma divergência ou corrupção de dados."
            )

    return summary


def is_running_from_removable() -> bool:
    """Verifica se o script/executável está sendo executado a partir de um pendrive/mídia removível."""
    try:
        current_path = os.path.abspath(sys.argv[0])
        if sys.platform == "win32":
            drive = os.path.splitdrive(current_path)[0] + "\\"
            import ctypes
            drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive)
            return drive_type == 2
        return False
    except Exception:
        return False
