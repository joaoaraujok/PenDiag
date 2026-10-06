"""
Coletor de integridade e saúde de bateria (desgaste, capacidade nominal e ciclos).
"""

import os
import sys
import tempfile
import subprocess
import xml.etree.ElementTree as ET
from typing import Optional, Tuple
import psutil

from pendiag.models import BatteryReport


def _extract_windows_battery_capacities() -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """
    Extrai capacidades em mWh (DesignCapacity, FullChargeCapacity, CycleCount) no Windows.
    Retorna: (design_mwh, full_mwh, cycle_count)
    """
    design_mwh: Optional[int] = None
    full_mwh: Optional[int] = None
    cycles: Optional[int] = None

    # Método 1: powercfg /batteryreport /xml (mais confiável e padronizado em laptops modernos)
    tmp_path = os.path.join(tempfile.gettempdir(), f"pendiag_batt_{os.getpid()}.xml")
    try:
        proc = subprocess.run(
            ["powercfg", "/batteryreport", "/xml", "/output", tmp_path],
            capture_output=True, text=True, timeout=8
        )
        if proc.returncode == 0 and os.path.exists(tmp_path):
            try:
                tree = ET.parse(tmp_path)
                root = tree.getroot()
                # O XML utiliza namespace http://schemas.microsoft.com/battery/2012
                # Buscamos elementos ignorando namespace
                for elem in root.iter():
                    tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                    text = (elem.text or "").strip()
                    if tag == "DesignCapacity" and text.isdigit() and design_mwh is None:
                        design_mwh = int(text)
                    elif tag == "FullChargeCapacity" and text.isdigit() and full_mwh is None:
                        full_mwh = int(text)
                    elif tag == "CycleCount" and text.isdigit() and cycles is None:
                        cycles = int(text)
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
    except Exception:
        pass

    # Método 2: WMI fallback caso powercfg não tenha retornado capacidades
    if design_mwh is None or full_mwh is None:
        try:
            cmd = "Get-CimInstance -Namespace root/wmi -ClassName BatteryFullChargedCapacity | Select-Object -ExpandProperty FullChargedCapacity"
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True, text=True, timeout=5
            )
            if proc.returncode == 0 and proc.stdout.strip().isdigit():
                full_mwh = int(proc.stdout.strip())
        except Exception:
            pass

    return design_mwh, full_mwh, cycles


def _extract_linux_battery_capacities() -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """Extrai capacidades da bateria no Linux a partir de /sys/class/power_supply/."""
    design_mwh: Optional[int] = None
    full_mwh: Optional[int] = None
    cycles: Optional[int] = None

    base_dir = "/sys/class/power_supply"
    if not os.path.isdir(base_dir):
        return None, None, None

    for item in os.listdir(base_dir):
        if item.startswith("BAT"):
            bat_path = os.path.join(base_dir, item)
            
            def read_val(fname: str) -> Optional[int]:
                p = os.path.join(bat_path, fname)
                if os.path.exists(p):
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            c = f.read().strip()
                            return int(c) if c.isdigit() else None
                    except Exception:
                        pass
                return None

            # Pode estar em µWh (energy_*) ou µAh (charge_*)
            design = read_val("energy_full_design") or read_val("charge_full_design")
            full = read_val("energy_full") or read_val("charge_full")
            cycle = read_val("cycle_count")

            if design:
                design_mwh = design // 1000 if design > 100000 else design
            if full:
                full_mwh = full // 1000 if full > 100000 else full
            if cycle:
                cycles = cycle
            break

    return design_mwh, full_mwh, cycles


def collect_battery_report() -> BatteryReport:
    """Coleta e calcula métricas completas de saúde e integridade da bateria."""
    try:
        ps_batt = psutil.sensors_battery()
    except Exception:
        ps_batt = None

    if ps_batt is None:
        return BatteryReport(
            present=False,
            status_text="Não detectada (Computador Desktop ou alimentação AC fixa)",
            health_rating="N/A"
        )

    percent = float(ps_batt.percent)
    plugged = bool(ps_batt.power_plugged)
    
    # Tempo restante
    secs_left = ps_batt.secsleft
    time_left_min = None
    if secs_left and secs_left > 0:
        time_left_min = int(secs_left / 60)

    # Detalhes de Degradação / Wear Level
    design_mwh, full_mwh, cycles = None, None, None
    if sys.platform == "win32":
        design_mwh, full_mwh, cycles = _extract_windows_battery_capacities()
    elif sys.platform.startswith("linux"):
        design_mwh, full_mwh, cycles = _extract_linux_battery_capacities()

    wear_percent = None
    health_percent = None
    rating = "BOM"

    if design_mwh and full_mwh and design_mwh > 0:
        health_percent = round((full_mwh / design_mwh) * 100, 1)
        # Limita para no máximo 100% (baterias novas podem reportar ligeiramente > 100%)
        health_percent = min(100.0, health_percent)
        wear_percent = round(100.0 - health_percent, 1)
        wear_percent = max(0.0, wear_percent)

        if health_percent >= 85.0:
            rating = "EXCELENTE"
        elif health_percent >= 70.0:
            rating = "BOM"
        elif health_percent >= 50.0:
            rating = "DEGRADADA"
        else:
            rating = "CRITICA"
    else:
        # Se não foi possível obter capacidade projetada, avalia pelo percentual atual
        rating = "OK"

    status_str = f"{percent:.0f}% - "
    if plugged:
        status_str += "Conectada à tomada (Carregando / 100%)"
    else:
        if time_left_min:
            h, m = divmod(time_left_min, 60)
            status_str += f"Em uso na bateria (Restam ~{h}h {m}m)"
        else:
            status_str += "Em uso na bateria"

    return BatteryReport(
        present=True,
        percent=percent,
        power_plugged=plugged,
        time_left_minutes=time_left_min,
        design_capacity_mwh=design_mwh,
        full_charge_capacity_mwh=full_mwh,
        wear_level_percent=wear_percent,
        health_percent=health_percent,
        cycle_count=cycles,
        status_text=status_str,
        health_rating=rating
    )
