"""
Coletor de informações de armazenamento, discos físicos, saúde S.M.A.R.T. e partições.
Com detecção de executável smartctl embutido em pendrive e consultas WMI/CIM expandidas.
"""

import sys
import os
import shutil
import subprocess
import json
from typing import List, Dict, Any, Optional
import psutil

from pendiag.models import DiskDevice, PartitionInfo, DiskReport


def _find_smartctl_binary() -> Optional[str]:
    """
    Localiza o executável smartctl (Smartmontools) no PATH do sistema operacional
    ou em pastas de ferramentas no pendrive (ex: tools/smartctl.exe).
    """
    # 1. Verifica PATH do sistema
    bin_path = shutil.which("smartctl")
    if bin_path:
        return bin_path

    # 2. Candidatos relativos à estrutura do pendrive
    candidates = [
        "tools/smartctl.exe",
        "tools/smartctl",
        "tools/bin/smartctl.exe",
        "tools/bin/smartctl",
        "bin/smartctl.exe",
        "bin/smartctl",
        "smartctl.exe",
        "smartctl"
    ]

    base_dirs = [
        os.getcwd(),
        os.path.dirname(os.path.abspath(__file__)),
        os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")),
        os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    ]

    if sys.platform == "win32":
        try:
            drive_root = os.path.splitdrive(os.path.abspath(sys.argv[0]))[0] + "\\"
            base_dirs.append(drive_root)
        except Exception:
            pass

    for b in base_dirs:
        for c in candidates:
            target = os.path.join(b, c)
            if os.path.isfile(target):
                return os.path.abspath(target)

    return None


def _query_smartctl() -> Dict[str, Any]:
    """Tenta executar smartctl se disponível no sistema ou no pendrive."""
    smartctl_bin = _find_smartctl_binary()
    if not smartctl_bin:
        return {}
    
    results = {}
    try:
        scan_proc = subprocess.run(
            [smartctl_bin, "--scan", "--json=c"],
            capture_output=True, text=True, timeout=5
        )
        if scan_proc.returncode == 0 and scan_proc.stdout.strip():
            scan_data = json.loads(scan_proc.stdout)
            devices = scan_data.get("devices", [])
            for dev in devices:
                dev_name = dev.get("name")
                if not dev_name:
                    continue
                info_proc = subprocess.run(
                    [smartctl_bin, "-x", "--json=c", dev_name],
                    capture_output=True, text=True, timeout=6
                )
                if info_proc.stdout.strip():
                    try:
                        results[dev_name] = json.loads(info_proc.stdout)
                    except Exception:
                        pass
    except Exception:
        pass
    return results


def _extract_smartctl_metrics(dev_smart: Dict[str, Any]) -> tuple[Optional[float], Optional[float]]:
    """Extrai temperatura em °C e desgaste em % a partir da saída JSON do smartctl."""
    temp_c = None
    wear_pct = None

    # Temperatura
    if "temperature" in dev_smart and "current" in dev_smart["temperature"]:
        try:
            temp_c = float(dev_smart["temperature"]["current"])
        except Exception:
            pass

    # Desgaste NVMe (percentage_used)
    nvme_log = dev_smart.get("nvme_smart_health_information_log", {})
    if "percentage_used" in nvme_log:
        try:
            wear_pct = float(nvme_log["percentage_used"])
        except Exception:
            pass

    # Atributos ATA SMART (SSD Wear / Life remaining)
    ata_attrs = dev_smart.get("ata_smart_attributes", {}).get("table", [])
    for attr in ata_attrs:
        attr_id = attr.get("id")
        attr_name = (attr.get("name") or "").lower()
        # Temperatura (ID 194 ou 190)
        if attr_id in [194, 190] and temp_c is None:
            try:
                temp_c = float(attr.get("raw", {}).get("value", 0))
            except Exception:
                pass
        # Desgaste / Vida útil (ID 231, 233, 173, 202)
        if (attr_id in [231, 173, 202] or "wear" in attr_name or "endurance" in attr_name) and wear_pct is None:
            try:
                # Se for atributo de porcentagem restante de vida, desgastado = 100 - restante
                raw_val = float(attr.get("value", 100))
                if "remaining" in attr_name or "life" in attr_name:
                    wear_pct = max(0.0, 100.0 - raw_val)
                else:
                    wear_pct = raw_val
            except Exception:
                pass

    return temp_c, wear_pct


def _collect_windows_physical_disks() -> List[DiskDevice]:
    """Coleta discos físicos, dados do MSFT_PhysicalDisk e confiabilidade no Windows."""
    disks: List[DiskDevice] = []

    # 1. Consulta Get-PhysicalDisk com campos estendidos
    try:
        cmd = (
            "Get-PhysicalDisk | Select-Object DeviceId, FriendlyName, MediaType, HealthStatus, "
            "OperationalStatus, Size, BusType, SerialNumber, Usage, SpindleSpeed, AllocatedSize | ConvertTo-Json"
        )
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=6
        )
        if proc.returncode == 0 and proc.stdout.strip():
            data = json.loads(proc.stdout)
            items = data if isinstance(data, list) else [data]
            for item in items:
                dev_id = str(item.get("DeviceId", ""))
                name = item.get("FriendlyName") or f"Disco Físico #{dev_id}"
                mtype = item.get("MediaType") or "Desconhecido"
                health = item.get("HealthStatus") or "OK"
                op_status = item.get("OperationalStatus") or "OK"
                size = int(item.get("Size") or 0)
                bus = item.get("BusType")
                serial = item.get("SerialNumber")
                spindle = item.get("SpindleSpeed")
                alloc_size = item.get("AllocatedSize")

                # Se spindle speed for 0 e media type não definida, é SSD
                if spindle == 0 and mtype in ["Unspecified", "Desconhecido"]:
                    mtype = "SSD"

                is_ok = health.lower() in ["healthy", "ok"] and op_status.lower() in ["ok"]

                disks.append(DiskDevice(
                    device_id=dev_id,
                    name=name,
                    media_type=mtype,
                    size_bytes=size,
                    health_status=health,
                    operational_status=op_status,
                    bus_type=bus,
                    serial_number=serial,
                    is_smart_ok=is_ok,
                    spindle_speed_rpm=int(spindle) if spindle is not None else None,
                    allocated_size_bytes=int(alloc_size) if alloc_size is not None else None
                ))
    except Exception:
        pass

    # 2. Tenta coletar StorageReliabilityCounter (Temperatura / Desgaste nativo do Windows)
    try:
        cmd_rel = (
            "Get-PhysicalDisk | Get-StorageReliabilityCounter | "
            "Select-Object DeviceId, Temperature, Wear | ConvertTo-Json"
        )
        proc_rel = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd_rel],
            capture_output=True, text=True, timeout=4
        )
        if proc_rel.returncode == 0 and proc_rel.stdout.strip():
            r_data = json.loads(proc_rel.stdout)
            r_items = r_data if isinstance(r_data, list) else [r_data]
            for r in r_items:
                r_dev_id = str(r.get("DeviceId", ""))
                r_temp = r.get("Temperature")
                r_wear = r.get("Wear")
                for d in disks:
                    if d.device_id == r_dev_id:
                        if r_temp and r_temp > 0 and r_temp < 150:
                            d.temperature_c = float(r_temp)
                        if r_wear is not None:
                            d.wear_percent = float(r_wear)
    except Exception:
        pass

    # 3. Fallback para Win32_DiskDrive caso Get-PhysicalDisk falhe
    if not disks:
        try:
            cmd = "Get-CimInstance Win32_DiskDrive | Select-Object DeviceID, Model, Status, InterfaceType, MediaType, Size, SerialNumber | ConvertTo-Json"
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True, text=True, timeout=6
            )
            if proc.returncode == 0 and proc.stdout.strip():
                data = json.loads(proc.stdout)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    dev_id = item.get("DeviceID", "")
                    model = item.get("Model") or "Disco Desconhecido"
                    status = item.get("Status") or "OK"
                    size = int(item.get("Size") or 0)
                    interface_type = item.get("InterfaceType") or "Desconhecido"
                    serial = item.get("SerialNumber")

                    is_ok = status.upper() == "OK"

                    disks.append(DiskDevice(
                        device_id=dev_id,
                        name=model,
                        media_type="SSD/HDD",
                        size_bytes=size,
                        health_status=status,
                        operational_status=status,
                        bus_type=interface_type,
                        serial_number=serial,
                        is_smart_ok=is_ok
                    ))
        except Exception:
            pass

    return disks


def _collect_linux_physical_disks() -> List[DiskDevice]:
    """Coleta discos físicos no Linux via lsblk."""
    disks: List[DiskDevice] = []
    try:
        proc = subprocess.run(
            ["lsblk", "-d", "-J", "-b", "-o", "NAME,MODEL,ROTA,SIZE,TRAN,SERIAL"],
            capture_output=True, text=True, timeout=5
        )
        if proc.returncode == 0 and proc.stdout.strip():
            data = json.loads(proc.stdout)
            for block in data.get("blockdevices", []):
                name = block.get("name", "")
                model = (block.get("model") or "").strip() or f"/dev/{name}"
                is_rotational = block.get("rota")
                mtype = "HDD" if is_rotational else "SSD/NVMe"
                size = int(block.get("size") or 0)
                bus = block.get("tran") or "Desconhecido"
                serial = (block.get("serial") or "").strip() or None

                disks.append(DiskDevice(
                    device_id=f"/dev/{name}",
                    name=model,
                    media_type=mtype,
                    size_bytes=size,
                    health_status="OK",
                    operational_status="OK",
                    bus_type=bus,
                    serial_number=serial,
                    is_smart_ok=True,
                    spindle_speed_rpm=5400 if is_rotational else 0
                ))
    except Exception:
        pass
    return disks


def collect_disk_report() -> DiskReport:
    """Coleta informações de discos físicos, saúde e partições ativas."""
    if sys.platform == "win32":
        disks = _collect_windows_physical_disks()
    elif sys.platform.startswith("linux"):
        disks = _collect_linux_physical_disks()
    else:
        disks = []

    # Enriquece com dados de smartctl se disponível (local ou pendrive)
    smart_data = _query_smartctl()
    if smart_data:
        for d in disks:
            for dev_key, dev_smart in smart_data.items():
                if d.device_id in dev_key or (d.serial_number and d.serial_number in str(dev_smart)):
                    d.smart_attributes = dev_smart
                    smart_passed = dev_smart.get("smart_status", {}).get("passed", True)
                    d.is_smart_ok = smart_passed
                    if not smart_passed:
                        d.health_status = "Unhealthy"

                    # Extrai temperatura e desgaste
                    temp, wear = _extract_smartctl_metrics(dev_smart)
                    if temp is not None:
                        d.temperature_c = temp
                    if wear is not None:
                        d.wear_percent = wear

    # Partições e Pontos de Montagem
    partitions: List[PartitionInfo] = []
    try:
        parts = psutil.disk_partitions(all=False)
        for p in parts:
            try:
                if sys.platform == "win32" and "cdrom" in p.opts.lower():
                    continue
                usage = psutil.disk_usage(p.mountpoint)
                partitions.append(PartitionInfo(
                    device=p.device,
                    mountpoint=p.mountpoint,
                    fstype=p.fstype,
                    total_bytes=usage.total,
                    used_bytes=usage.used,
                    free_bytes=usage.free,
                    usage_percent=usage.percent
                ))
            except (PermissionError, OSError):
                continue
    except Exception:
        pass

    # Status geral de saúde
    overall_health = "OK"
    for d in disks:
        h = (d.health_status or "").lower()
        if h in ["unhealthy", "failing", "bad", "critico", "falha"]:
            overall_health = "CRITICAL"
            break
        elif h in ["warning", "degraded", "atencao"]:
            overall_health = "WARNING"

    return DiskReport(
        disks=disks,
        partitions=partitions,
        overall_health=overall_health
    )
