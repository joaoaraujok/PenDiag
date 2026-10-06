"""
Interface de Linha de Comando (CLI) profissional com Typer e Rich.
"""

import os
import sys
import webbrowser
from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich import box

from pendiag import __version__
from pendiag.models import (
    DiagnosticReport,
    BenchmarkReport
)
from pendiag.collectors.system import collect_system_info
from pendiag.collectors.disk import collect_disk_report
from pendiag.collectors.battery import collect_battery_report
from pendiag.collectors.network import collect_network_report
from pendiag.benchmarks.memory_test import run_memory_benchmark
from pendiag.benchmarks.disk_test import run_disk_block_benchmark
from pendiag.utils import (
    format_bytes,
    format_speed,
    evaluate_health,
    generate_executive_summary,
    is_running_from_removable
)
from pendiag.exporters.json_exporter import save_json_report
from pendiag.exporters.html_exporter import save_html_report
from pendiag.exporters.webhook import send_report_webhook

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

app = typer.Typer(
    name="pendiag",
    help="⚡ PenDiag - CLI de Diagnóstico Rápido de Hardware e Rede em Pendrive",
    add_completion=False
)

console = Console(legacy_windows=False)


def print_banner():
    """Exibe o cabeçalho estilizado do PenDiag."""
    removable_badge = "[bold yellow][PENDRIVE / MÍDIA REMOVÍVEL][/bold yellow]" if is_running_from_removable() else "[dim][MODO LOCAL][/dim]"
    banner_text = Text()
    banner_text.append("⚡ PenDiag ", style="bold cyan")
    banner_text.append(f"v{__version__} ", style="bold white")
    banner_text.append("• Diagnóstico de Hardware, Discos, Bateria e Rede\n", style="dim")
    banner_text.append(f"Ambiente: {sys.platform.upper()} ", style="green")
    banner_text.append(f"{removable_badge}\n", style="none")
    banner_text.append(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", style="dim")

    console.print(Panel(
        banner_text,
        border_style="cyan",
        box=box.ROUNDED,
        title="[bold white]SUÍTE TÉCNICA DE ATENDIMENTO[/bold white]",
        title_align="left"
    ))


def display_system_table(report: DiagnosticReport):
    """Renderiza a tabela de informações de sistema, CPU, RAM, Antivírus e Temperatura."""
    sys_info = report.system
    if not sys_info:
        return

    table = Table(title="[bold cyan]💻 Identificação & Recursos do Sistema[/bold cyan]", box=box.ROUNDED)
    table.add_column("Propriedade", style="cyan", no_wrap=True)
    table.add_column("Detalhe", style="white")

    table.add_row("Hostname", sys_info.hostname)
    table.add_row("Sistema Operacional", f"{sys_info.os_name} {sys_info.os_release} ({sys_info.architecture})")
    table.add_row("Fabricante / Modelo", f"{sys_info.manufacturer or 'N/A'} {sys_info.model or ''}")
    table.add_row("Serial / Service Tag", sys_info.serial_number or "N/A")
    table.add_row("Versão da BIOS", sys_info.bios_version or "N/A")
    table.add_row("Processador", f"{sys_info.cpu_model} ({sys_info.cpu_physical_cores}C/{sys_info.cpu_logical_cores}T)")

    # Temperatura do Processador se disponível
    if sys_info.cpu_temperature_c is not None:
        t_style = "bold red" if sys_info.cpu_temperature_c >= 85 else ("bold yellow" if sys_info.cpu_temperature_c >= 75 else "bold green")
        table.add_row("Temperatura da CPU", f"[{t_style}]{sys_info.cpu_temperature_c:.1f} °C[/{t_style}]")

    cpu_usage_style = "bold red" if sys_info.cpu_usage_percent > 85 else ("bold yellow" if sys_info.cpu_usage_percent > 70 else "bold green")
    table.add_row("Uso de CPU Atual", f"[{cpu_usage_style}]{sys_info.cpu_usage_percent}%[/{cpu_usage_style}]")

    ram_usage_style = "bold red" if sys_info.ram_usage_percent > 90 else ("bold yellow" if sys_info.ram_usage_percent > 80 else "bold green")
    table.add_row(
        "Memória RAM",
        f"[{ram_usage_style}]{format_bytes(sys_info.ram_used_bytes)} / {format_bytes(sys_info.ram_total_bytes)} ({sys_info.ram_usage_percent}% em uso)[/{ram_usage_style}]"
    )

    # Antivírus e Segurança
    if sys_info.antivirus_name:
        av_st = "Ativo" if sys_info.antivirus_enabled else "Inativo"
        av_color = "bold green" if sys_info.antivirus_enabled else "bold red"
        up_text = " (Definições Atualizadas)" if sys_info.antivirus_updated else " (Desatualizado)"
        table.add_row("Proteção Antivírus", f"[{av_color}]{sys_info.antivirus_name} - {av_st}{up_text}[/{av_color}]")

    table.add_row("Uptime do Sistema", sys_info.uptime_human)

    console.print(table)


def display_disk_tables(report: DiagnosticReport):
    """Renderiza tabelas de discos físicos e partições."""
    if not report.disk:
        return

    # 1. Discos Físicos
    if report.disk.disks:
        d_table = Table(title="[bold cyan]💽 Discos Físicos & S.M.A.R.T.[/bold cyan]", box=box.ROUNDED)
        d_table.add_column("ID", style="dim", no_wrap=True)
        d_table.add_column("Modelo / Descrição", style="white")
        d_table.add_column("Tipo", style="cyan")
        d_table.add_column("Tamanho", style="white")
        d_table.add_column("Saúde S.M.A.R.T.", style="bold")
        d_table.add_column("Status Operacional", style="white")
        d_table.add_column("Temperatura", style="white")
        d_table.add_column("Desgaste", style="white")

        for d in report.disk.disks:
            h_style = "green" if d.is_smart_ok else "red"
            temp_str = f"{d.temperature_c:.0f}°C" if d.temperature_c is not None else "-"
            wear_str = f"{d.wear_percent:.0f}%" if d.wear_percent is not None else "-"
            d_table.add_row(
                str(d.device_id),
                d.name,
                f"{d.media_type} ({d.bus_type or 'Local'})",
                format_bytes(d.size_bytes),
                f"[{h_style}]{d.health_status}[/{h_style}]",
                d.operational_status,
                temp_str,
                wear_str
            )
        console.print(d_table)

    # 2. Partições
    if report.disk.partitions:
        p_table = Table(title="[bold cyan]📁 Partições & Armazenamento em Volumes[/bold cyan]", box=box.ROUNDED)
        p_table.add_column("Ponto", style="cyan", no_wrap=True)
        p_table.add_column("Tipo", style="dim")
        p_table.add_column("Total", style="white")
        p_table.add_column("Usado", style="white")
        p_table.add_column("Livre", style="white")
        p_table.add_column("Uso %", style="bold")

        for p in report.disk.partitions:
            u_style = "red" if p.usage_percent > 90 else ("yellow" if p.usage_percent > 80 else "green")
            p_table.add_row(
                p.mountpoint,
                p.fstype,
                format_bytes(p.total_bytes),
                format_bytes(p.used_bytes),
                format_bytes(p.free_bytes),
                f"[{u_style}]{p.usage_percent}%[/{u_style}]"
            )
        console.print(p_table)


def display_battery_table(report: DiagnosticReport):
    """Renderiza tabela com métricas de bateria e desgaste."""
    b = report.battery
    if not b:
        return

    table = Table(title="[bold cyan]🔋 Integridade e Desgaste da Bateria[/bold cyan]", box=box.ROUNDED)
    table.add_column("Métrica", style="cyan", no_wrap=True)
    table.add_column("Valor", style="white")

    if not b.present:
        table.add_row("Estado", "[dim]Não detectada (Computador Desktop ou alimentação AC)[/dim]")
        console.print(table)
        return

    table.add_row("Nível de Carga Atual", f"[bold green]{b.percent}%[/bold green]")
    table.add_row("Conectado à Tomada", "Sim (Carregando / AC)" if b.power_plugged else "Não (Em uso na bateria)")

    if b.health_percent is not None:
        h_color = "green" if b.health_percent >= 80 else ("yellow" if b.health_percent >= 65 else "red")
        table.add_row("Saúde da Bateria", f"[{h_color}]{b.health_percent}% da capacidade de projeto[/{h_color}]")

    if b.wear_level_percent is not None:
        w_color = "red" if b.wear_level_percent > 30 else ("yellow" if b.wear_level_percent > 15 else "green")
        table.add_row("Nível de Desgaste (Wear)", f"[{w_color}]{b.wear_level_percent}%[/{w_color}]")

    if b.design_capacity_mwh and b.full_charge_capacity_mwh:
        table.add_row("Capacidade Original / Atual", f"{b.design_capacity_mwh} mWh / {b.full_charge_capacity_mwh} mWh")

    if b.cycle_count:
        table.add_row("Ciclos de Recarga", str(b.cycle_count))

    table.add_row("Classificação Geral", f"[bold]{b.health_rating}[/bold]")
    console.print(table)


def display_network_tables(report: DiagnosticReport):
    """Renderiza tabelas de conectividade, ping e DNS."""
    net = report.network
    if not net:
        return

    # Ping / ICMP Table
    if net.ping_tests:
        p_table = Table(title="[bold cyan]🌐 Testes de Latência & Perda de Pacotes (Ping)[/bold cyan]", box=box.ROUNDED)
        p_table.add_column("Alvo", style="white")
        p_table.add_column("Protocolo", style="dim")
        p_table.add_column("Enviados/Rec.", style="white")
        p_table.add_column("Perda %", style="bold")
        p_table.add_column("Mínimo", style="white")
        p_table.add_column("Médio (RTT)", style="bold cyan")
        p_table.add_column("Máximo", style="white")
        p_table.add_column("Status", style="bold")

        for p in net.ping_tests:
            loss_style = "green" if p.packet_loss_percent == 0 else ("yellow" if p.packet_loss_percent < 50 else "red")
            st_style = "green" if "OK" in p.status else "red"
            min_str = f"{p.min_rtt_ms} ms" if p.min_rtt_ms is not None else "-"
            avg_str = f"{p.avg_rtt_ms} ms" if p.avg_rtt_ms is not None else "-"
            max_str = f"{p.max_rtt_ms} ms" if p.max_rtt_ms is not None else "-"
            p_table.add_row(
                p.target,
                p.protocol,
                f"{p.packets_sent}/{p.packets_received}",
                f"[{loss_style}]{p.packet_loss_percent}%[/{loss_style}]",
                min_str,
                avg_str,
                max_str,
                f"[{st_style}]{p.status}[/{st_style}]"
            )
        console.print(p_table)

    # DNS Resolution Table
    if net.dns_tests:
        d_table = Table(title="[bold cyan]🔍 Resolução de Nomes (DNS)[/bold cyan]", box=box.ROUNDED)
        d_table.add_column("Domínio", style="white")
        d_table.add_column("IP Resolvido", style="cyan")
        d_table.add_column("Tempo (ms)", style="bold")
        d_table.add_column("Status", style="bold")

        for d in net.dns_tests:
            st = "[green]OK[/green]" if d.success else "[red]FALHA[/red]"
            lat_str = f"{d.latency_ms} ms" if d.latency_ms is not None else "-"
            d_table.add_row(
                d.domain,
                d.resolved_ip or (d.error or "Falha"),
                lat_str,
                st
            )
        console.print(d_table)


def display_benchmark_table(report: DiagnosticReport):
    """Renderiza resultados dos testes de estresse e integridade."""
    bench = report.benchmark
    if not bench:
        return

    table = Table(title="[bold cyan]🚀 Benchmarks de Memória RAM e Bloco de Disco[/bold cyan]", box=box.ROUNDED)
    table.add_column("Teste Realizado", style="cyan", no_wrap=True)
    table.add_column("Velocidade Escrita", style="white")
    table.add_column("Velocidade Leitura", style="white")
    table.add_column("Integridade SHA-256", style="bold")
    table.add_column("Duração", style="dim")

    if bench.memory_benchmark:
        m = bench.memory_benchmark
        m_int = "[green]✓ 100% CONFIRMADA[/green]" if m.integrity_verified else "[red]✗ CORRUPÇÃO DETECTADA[/red]"
        label = f"Memória RAM ({m.buffer_size_mb} MB)"
        if m.ram_adjusted:
            label += " [dim]*ajustado[/dim]"
        table.add_row(
            label,
            format_speed(m.write_speed_mb_s),
            format_speed(m.read_speed_mb_s),
            m_int,
            f"{m.duration_seconds}s"
        )

    if bench.disk_benchmark:
        d = bench.disk_benchmark
        d_int = "[green]✓ 100% CONFIRMADA[/green]" if d.integrity_verified else "[red]✗ CORRUPÇÃO DETECTADA[/red]"
        table.add_row(
            f"Bloco de Disco fsync ({d.total_size_mb} MB)",
            format_speed(d.write_speed_mb_s),
            format_speed(d.read_speed_mb_s),
            d_int,
            f"{d.duration_seconds}s"
        )

    console.print(table)


def display_health_summary(report: DiagnosticReport):
    """Exibe painel de pontuação final, lista de alertas e parecer executivo."""
    sc = report.health_score
    status = report.overall_status

    if sc >= 85:
        color = "green"
        emoji = "🛡️"
    elif sc >= 60:
        color = "yellow"
        emoji = "⚠️"
    else:
        color = "red"
        emoji = "🚨"

    summary_text = Text()
    summary_text.append(f"{emoji} PONTUAÇÃO DE SAÚDE DO EQUIPAMENTO: ", style="bold white")
    summary_text.append(f"{sc}/100 ", style=f"bold {color}")
    summary_text.append(f"[{status}]\n", style=f"bold {color}")

    if report.alerts:
        summary_text.append("\nObservações e Alertas Críticos Identificados:\n", style="bold white")
        for alert in report.alerts:
            a_style = "bold red" if alert.level == "CRITICAL" else ("bold yellow" if alert.level == "WARNING" else "cyan")
            summary_text.append(f" • [{alert.category}] ", style=a_style)
            summary_text.append(f"{alert.message}\n", style="white")
    else:
        summary_text.append("\n✓ Nenhum problema crítico de hardware, disco ou rede foi detectado.", style="green")

    console.print(Panel(
        summary_text,
        border_style=color,
        box=box.ROUNDED,
        title="[bold white]RESUMO DO DIAGNÓSTICO[/bold white]",
        title_align="left"
    ))

    # Exibição do Parecer Técnico Comercial (Laudo Executivo)
    if report.executive_summary:
        console.print()
        exec_text = Text()
        for idx, item in enumerate(report.executive_summary, 1):
            clean_item = item.replace("**", "").replace("🛡️ ", "").replace("⚠️ ", "").replace("🚨 ", "").replace("✅ ", "").replace("✓ ", "").replace("ℹ️ ", "").replace("⚡ ", "").replace("🔋 ", "")
            exec_text.append(f"{idx}. ", style="bold cyan")
            exec_text.append(f"{clean_item}\n\n", style="white")

        console.print(Panel(
            exec_text,
            border_style="cyan",
            box=box.ROUNDED,
            title="[bold white]💼 PARECER TÉCNICO COMERCIAL (LAUDO EXECUTIVO PARA CLIENTE)[/bold white]",
            title_align="left"
        ))


@app.command("all")
def diagnose_all(
    output_dir: str = typer.Option("./reports", "--output-dir", "-o", help="Diretório onde salvar os relatórios."),
    export_format: str = typer.Option("all", "--format", "-f", help="Formato de exportação: all, html, json, none."),
    quick: bool = typer.Option(False, "--quick", "-q", help="Modo rápido: reduz tamanho dos testes de escrita em memória e disco."),
    mem_size_mb: int = typer.Option(64, "--mem-mb", help="Tamanho em MB para teste de memória RAM."),
    disk_size_mb: int = typer.Option(32, "--disk-mb", help="Tamanho em MB para teste de bloco em disco."),
    send_url: Optional[str] = typer.Option(None, "--send-url", help="URL HTTP para envio automático do diagnóstico via POST."),
    technician: Optional[str] = typer.Option(None, "--technician", "-t", help="Nome do técnico responsável."),
    ticket: Optional[str] = typer.Option(None, "--ticket", help="Número do chamado / OS."),
    open_browser: bool = typer.Option(False, "--open-browser", help="Abrir automaticamente o relatório HTML no navegador.")
):
    """
    Executa o diagnóstico completo: Sistema, Discos, S.M.A.R.T., Bateria, Rede e Benchmarks de I/O.
    """
    print_banner()

    report = DiagnosticReport(
        technician_name=technician,
        ticket_id=ticket
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:

        # 1. Sistema
        t_sys = progress.add_task("[cyan]Coletando métricas de CPU, RAM, Antivírus e Sistema...", total=1)
        report.system = collect_system_info()
        progress.update(t_sys, completed=1)

        # 2. Armazenamento e SMART
        t_disk = progress.add_task("[cyan]Analisando discos físicos e integridade S.M.A.R.T....", total=1)
        report.disk = collect_disk_report()
        progress.update(t_disk, completed=1)

        # 3. Bateria
        t_batt = progress.add_task("[cyan]Verificando bateria, desgaste e capacidade nominal...", total=1)
        report.battery = collect_battery_report()
        progress.update(t_batt, completed=1)

        # 4. Rede
        t_net = progress.add_task("[cyan]Testando adaptadores de rede, ping e resolução DNS...", total=1)
        report.network = collect_network_report()
        progress.update(t_net, completed=1)

        # 5. Benchmarks
        bench_report = BenchmarkReport()
        actual_mem_mb = 16 if quick else mem_size_mb
        actual_disk_mb = 8 if quick else disk_size_mb

        t_mem = progress.add_task(f"[cyan]Executando teste de escrita/leitura em RAM ({actual_mem_mb} MB)...", total=1)
        bench_report.memory_benchmark = run_memory_benchmark(size_mb=actual_mem_mb)
        progress.update(t_mem, completed=1)

        t_blk = progress.add_task(f"[cyan]Executando teste de I/O em bloco de disco ({actual_disk_mb} MB)...", total=1)
        bench_report.disk_benchmark = run_disk_block_benchmark(size_mb=actual_disk_mb)
        progress.update(t_blk, completed=1)

        report.benchmark = bench_report

    # Avaliação de Saúde, Alertas e Parecer Comercial
    score, status, alerts = evaluate_health(report)
    report.health_score = score
    report.overall_status = status
    report.alerts = alerts
    report.executive_summary = generate_executive_summary(report)

    # Exibição no terminal
    console.print()
    display_system_table(report)
    console.print()
    display_disk_tables(report)
    console.print()
    display_battery_table(report)
    console.print()
    display_network_tables(report)
    console.print()
    display_benchmark_table(report)
    console.print()
    display_health_summary(report)

    # Exportação de Relatórios
    host = report.system.hostname if report.system else "host"
    timestamp_clean = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"diagnostico_{host}_{timestamp_clean}"

    saved_files = []
    if export_format.lower() in ["all", "json"]:
        json_path = os.path.join(output_dir, f"{base_filename}.json")
        saved_json = save_json_report(report, json_path)
        saved_files.append(saved_json)

    html_file = None
    if export_format.lower() in ["all", "html"]:
        html_path = os.path.join(output_dir, f"{base_filename}.html")
        html_file = save_html_report(report, html_path)
        saved_files.append(html_file)

    if saved_files:
        console.print()
        console.print(Panel(
            "\n".join([f"✓ [bold green]Arquivo salvo:[/bold green] {f}" for f in saved_files]),
            border_style="green",
            box=box.ROUNDED,
            title="[bold white]RELATÓRIOS EXPORTADOS[/bold white]"
        ))

    # Envio via Webhook se solicitado
    if send_url:
        console.print(f"[cyan]Transmitindo diagnóstico para {send_url}...[/cyan]")
        success, msg = send_report_webhook(report, send_url)
        if success:
            console.print(f"[bold green]✓ {msg}[/bold green]")
        else:
            console.print(f"[bold red]✗ {msg}[/bold red]")

    # Abertura automática no navegador
    if open_browser and html_file:
        try:
            webbrowser.open(f"file:///{os.path.abspath(html_file)}")
        except Exception:
            pass


@app.command("sys")
def cmd_sys():
    """Exibe métricas detalhadas de CPU, Memória, SO, Placa-Mãe, BIOS e Antivírus."""
    print_banner()
    rep = DiagnosticReport()
    rep.system = collect_system_info()
    display_system_table(rep)


@app.command("disk")
def cmd_disk():
    """Analisa discos físicos, integridade S.M.A.R.T. e uso de partições."""
    print_banner()
    rep = DiagnosticReport()
    rep.disk = collect_disk_report()
    display_disk_tables(rep)


@app.command("battery")
def cmd_battery():
    """Diagnóstico de bateria: percentual, desgaste (wear level) e capacidade nominal."""
    print_banner()
    rep = DiagnosticReport()
    rep.battery = collect_battery_report()
    display_battery_table(rep)


@app.command("net")
def cmd_net():
    """Mede conectividade de rede, latência ICMP/Ping e tempo de resolução DNS."""
    print_banner()
    rep = DiagnosticReport()
    with console.status("[cyan]Executando testes de latência e resolução DNS...[/cyan]"):
        rep.network = collect_network_report()
    display_network_tables(rep)


@app.command("bench")
def cmd_bench(
    mem_size_mb: int = typer.Option(64, "--mem-mb", help="Tamanho em MB para teste de RAM."),
    disk_size_mb: int = typer.Option(32, "--disk-mb", help="Tamanho em MB para teste de bloco de disco.")
):
    """Executa testes de velocidade e integridade com SHA-256 em RAM e Bloco de Disco."""
    print_banner()
    rep = DiagnosticReport()
    b = BenchmarkReport()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        t_m = progress.add_task(f"[cyan]Testando Memória RAM ({mem_size_mb} MB)...", total=1)
        b.memory_benchmark = run_memory_benchmark(size_mb=mem_size_mb)
        progress.update(t_m, completed=1)

        t_d = progress.add_task(f"[cyan]Testando Bloco de Disco fsync ({disk_size_mb} MB)...", total=1)
        b.disk_benchmark = run_disk_block_benchmark(size_mb=disk_size_mb)
        progress.update(t_d, completed=1)

    rep.benchmark = b
    display_benchmark_table(rep)


def main():
    """Ponto de entrada principal."""
    if len(sys.argv) == 1:
        sys.argv.append("all")
    app()


if __name__ == "__main__":
    main()
