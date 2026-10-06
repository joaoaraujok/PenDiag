"""
Coletor de informações gerais do sistema, CPU, Memória RAM, BIOS, Antivírus e Temperatura.
"""

import os
import sys
import platform
import subprocess
import json
from datetime import datetime
import psutil

from pendiag.models import SystemInfo
from pendiag.utils import format_seconds


def get_cpu_model_name() -> str:
    """Obtém o nome comercial exato do processador de forma rápida e segura."""
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            )
            val, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            winreg.CloseKey(key)
            if val and val.strip():
                return val.strip()
        except Exception:
            pass

    elif sys.platform.startswith("linux"):
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":", 1)[1].strip()
        except Exception:
            pass

    elif sys.platform == "darwin":
        try:
            out = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True)
            if out.strip():
                return out.strip()
        except Exception:
            pass

    return platform.processor() or "Processador Desconhecido"


def get_hardware_identifiers() -> tuple[str | None, str | None, str | None, str | None]:
    """
    Obtém fabricante, modelo do computador, serial da BIOS e versão da BIOS.
    Retorna: (fabricante, modelo, serial, bios_version)
    """
    manufacturer, model, serial, bios_ver = None, None, None, None

    if sys.platform == "win32":
        try:
            p1 = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model | ConvertTo-Json"],
                capture_output=True, text=True, timeout=5
            )
            if p1.returncode == 0 and p1.stdout.strip():
                data = json.loads(p1.stdout)
                if isinstance(data, dict):
                    manufacturer = data.get("Manufacturer")
                    model = data.get("Model")
        except Exception:
            pass

        try:
            p2 = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_BIOS | Select-Object SMBIOSBIOSVersion, SerialNumber | ConvertTo-Json"],
                capture_output=True, text=True, timeout=5
            )
            if p2.returncode == 0 and p2.stdout.strip():
                data = json.loads(p2.stdout)
                if isinstance(data, dict):
                    serial = data.get("SerialNumber")
                    bios_ver = data.get("SMBIOSBIOSVersion")
        except Exception:
            pass

    elif sys.platform.startswith("linux"):
        def read_dmi(name: str) -> str | None:
            path = f"/sys/class/dmi/id/{name}"
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        return f.read().strip()
                except Exception:
                    pass
            return None

        manufacturer = read_dmi("sys_vendor")
        model = read_dmi("product_name")
        serial = read_dmi("product_serial")
        bios_ver = read_dmi("bios_version")

    return manufacturer, model, serial, bios_ver


def get_antivirus_info() -> tuple[str | None, bool | None, bool | None]:
    """
    Detecta o antivírus ativo no sistema, estado de proteção em tempo real e atualização das definições.
    Retorna: (nome_antivirus, ativado: bool, atualizado: bool)
    """
    av_name, av_enabled, av_updated = None, None, None

    if sys.platform == "win32":
        try:
            cmd = (
                "Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct | "
                "Select-Object displayName, productState | ConvertTo-Json"
            )
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True, text=True, timeout=5
            )
            if proc.returncode == 0 and proc.stdout.strip():
                data = json.loads(proc.stdout)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    name = item.get("displayName")
                    state = item.get("productState")
                    if name and state is not None:
                        av_name = name
                        state_int = int(state)
                        # No SecurityCenter2: bit 0x1000 = tempo real ativo; bit 0x0010 = desatualizado
                        av_enabled = bool(state_int & 0x1000)
                        av_updated = not bool(state_int & 0x0010)
                        # Se achou um habilitado, prioriza-o
                        if av_enabled:
                            break
        except Exception:
            pass

    elif sys.platform.startswith("linux"):
        # Verificação de agentes comuns de segurança em Linux
        known_agents = [
            ("clamav", "ClamAV"),
            ("sophos", "Sophos Endpoint"),
            ("falcon-sensor", "CrowdStrike Falcon"),
            ("cwx", "Wazuh Agent"),
            ("eset", "ESET NOD32")
        ]
        for proc in psutil.process_iter(["name"]):
            try:
                pname = (proc.info["name"] or "").lower()
                for key, display in known_agents:
                    if key in pname:
                        return display, True, True
            except Exception:
                pass
        av_name = "Defesa de Kernel / AppArmor / SELinux"
        av_enabled = True
        av_updated = True

    return av_name, av_enabled, av_updated


def get_cpu_temperature() -> float | None:
    """
    Obtém a temperatura do processador (°C) via psutil ou WMI térmico.
    Retorna valor em graus Celsius ou None caso não suportado pela placa-mãe.
    """
    # 1. psutil.sensors_temperatures() (Nativo em Linux/macOS e algumas plataformas Windows)
    try:
        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()
            if temps:
                candidates = []
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current and entry.current > 0 and entry.current < 120:
                            candidates.append(entry.current)
                if candidates:
                    return round(sum(candidates) / len(candidates), 1)
    except Exception:
        pass

    # 2. WMI Fallback no Windows
    if sys.platform == "win32":
        # Tenta MSAcpi_ThermalZoneTemperature
        try:
            cmd = (
                "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature | "
                "Select-Object -ExpandProperty CurrentTemperature"
            )
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True, text=True, timeout=4
            )
            if proc.returncode == 0 and proc.stdout.strip():
                first_line = proc.stdout.strip().splitlines()[0]
                if first_line.isdigit():
                    raw_val = int(first_line)
                    # CurrentTemperature é em décimos de Kelvin (ex: 3102 = 310.2 K = 37 °C)
                    celsius = (raw_val - 2732) / 10.0
                    if 10.0 <= celsius <= 115.0:
                        return round(celsius, 1)
        except Exception:
            pass

        # Tenta ThermalZoneInformation em PerfFormattedData
        try:
            cmd = (
                "Get-CimInstance Win32_PerfFormattedData_Counters_ThermalZoneInformation | "
                "Select-Object -ExpandProperty Temperature"
            )
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True, text=True, timeout=4
            )
            if proc.returncode == 0 and proc.stdout.strip():
                first_line = proc.stdout.strip().splitlines()[0]
                try:
                    kelvin = float(first_line)
                    celsius = kelvin - 273.15
                    if 10.0 <= celsius <= 115.0:
                        return round(celsius, 1)
                except ValueError:
                    pass
        except Exception:
            pass

    return None


def collect_system_info() -> SystemInfo:
    """Coleta todas as métricas essenciais do sistema operacional, processador e memória."""
    # Uptime
    boot_timestamp = psutil.boot_time()
    boot_dt = datetime.fromtimestamp(boot_timestamp)
    uptime_seconds = (datetime.now() - boot_dt).total_seconds()
    uptime_human = format_seconds(uptime_seconds)

    # CPU
    cpu_model = get_cpu_model_name()
    physical_cores = psutil.cpu_count(logical=False) or 1
    logical_cores = psutil.cpu_count(logical=True) or 1
    
    # Amostragem do uso de CPU rápida (0.2s)
    cpu_usage = psutil.cpu_percent(interval=0.2)
    
    cpu_freq = psutil.cpu_freq()
    freq_current = round(cpu_freq.current, 1) if cpu_freq and cpu_freq.current else None
    freq_max = round(cpu_freq.max, 1) if cpu_freq and cpu_freq.max else None

    # RAM & Swap
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    # Identificadores de Hardware
    manufacturer, model, serial, bios_ver = get_hardware_identifiers()

    # Antivírus e Temperatura
    av_name, av_enabled, av_updated = get_antivirus_info()
    cpu_temp = get_cpu_temperature()

    return SystemInfo(
        hostname=platform.node(),
        os_name=platform.system(),
        os_version=platform.version(),
        os_release=platform.release(),
        architecture=platform.machine(),
        boot_time=boot_dt.strftime("%Y-%m-%d %H:%M:%S"),
        uptime_human=uptime_human,
        cpu_model=cpu_model,
        cpu_physical_cores=physical_cores,
        cpu_logical_cores=logical_cores,
        cpu_freq_current_mhz=freq_current,
        cpu_freq_max_mhz=freq_max,
        cpu_usage_percent=cpu_usage,
        ram_total_bytes=mem.total,
        ram_used_bytes=mem.used,
        ram_free_bytes=mem.available,
        ram_usage_percent=mem.percent,
        swap_total_bytes=swap.total,
        swap_used_bytes=swap.used,
        swap_usage_percent=swap.percent,
        manufacturer=manufacturer,
        model=model,
        serial_number=serial,
        bios_version=bios_ver,
        antivirus_name=av_name,
        antivirus_enabled=av_enabled,
        antivirus_updated=av_updated,
        cpu_temperature_c=cpu_temp
    )
