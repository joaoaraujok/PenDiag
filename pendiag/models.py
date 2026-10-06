"""
Modelos de dados para o diagnóstico de hardware e rede.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


@dataclass
class DiagnosticAlert:
    level: str  # "INFO", "WARNING", "CRITICAL"
    category: str  # "SISTEMA", "DISCO", "BATERIA", "REDE", "MEMORIA", "SEGURANCA"
    message: str
    detail: Optional[str] = None


@dataclass
class SystemInfo:
    hostname: str
    os_name: str
    os_version: str
    os_release: str
    architecture: str
    boot_time: str
    uptime_human: str
    cpu_model: str
    cpu_physical_cores: int
    cpu_logical_cores: int
    cpu_freq_current_mhz: Optional[float]
    cpu_freq_max_mhz: Optional[float]
    cpu_usage_percent: float
    ram_total_bytes: int
    ram_used_bytes: int
    ram_free_bytes: int
    ram_usage_percent: float
    swap_total_bytes: int
    swap_used_bytes: int
    swap_usage_percent: float
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    bios_version: Optional[str] = None
    # Novos campos: Segurança e Temperatura
    antivirus_name: Optional[str] = None
    antivirus_enabled: Optional[bool] = None
    antivirus_updated: Optional[bool] = None
    cpu_temperature_c: Optional[float] = None


@dataclass
class DiskDevice:
    device_id: str
    name: str
    media_type: str  # "NVMe", "SSD", "HDD", "USB", "Desconhecido"
    size_bytes: int
    health_status: str  # "Healthy", "Warning", "Unhealthy", "OK", "Desconhecido"
    operational_status: str
    bus_type: Optional[str] = None
    serial_number: Optional[str] = None
    smart_attributes: Dict[str, Any] = field(default_factory=dict)
    is_smart_ok: bool = True
    # Novos campos expandidos de saúde e integridade
    temperature_c: Optional[float] = None
    wear_percent: Optional[float] = None
    spindle_speed_rpm: Optional[int] = None
    allocated_size_bytes: Optional[int] = None


@dataclass
class PartitionInfo:
    device: str
    mountpoint: str
    fstype: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    usage_percent: float


@dataclass
class DiskReport:
    disks: List[DiskDevice] = field(default_factory=list)
    partitions: List[PartitionInfo] = field(default_factory=list)
    overall_health: str = "OK"  # "OK", "WARNING", "CRITICAL"


@dataclass
class BatteryReport:
    present: bool
    percent: Optional[float] = None
    power_plugged: Optional[bool] = None
    time_left_minutes: Optional[int] = None
    design_capacity_mwh: Optional[int] = None
    full_charge_capacity_mwh: Optional[int] = None
    wear_level_percent: Optional[float] = None
    health_percent: Optional[float] = None
    cycle_count: Optional[int] = None
    status_text: str = "Não detectada"
    health_rating: str = "N/A"  # "EXCELENTE", "BOM", "DEGRADADA", "CRITICA", "N/A"


@dataclass
class NetworkInterface:
    name: str
    is_up: bool
    speed_mbps: Optional[int]
    ipv4_addresses: List[str] = field(default_factory=list)
    ipv6_addresses: List[str] = field(default_factory=list)
    mac_address: Optional[str] = None
    bytes_sent: int = 0
    bytes_recv: int = 0


@dataclass
class PingResult:
    target: str
    packets_sent: int
    packets_received: int
    packet_loss_percent: float
    min_rtt_ms: Optional[float]
    avg_rtt_ms: Optional[float]
    max_rtt_ms: Optional[float]
    protocol: str = "ICMP"
    success: bool = True
    status: str = "OK"
    note: Optional[str] = None


@dataclass
class DnsResult:
    domain: str
    dns_server: str
    resolved_ip: Optional[str]
    latency_ms: Optional[float]
    success: bool
    error: Optional[str] = None


@dataclass
class HttpResult:
    url: str
    status_code: Optional[int]
    latency_ms: Optional[float]
    success: bool
    error: Optional[str] = None


@dataclass
class NetworkReport:
    interfaces: List[NetworkInterface] = field(default_factory=list)
    dns_servers: List[str] = field(default_factory=list)
    gateway_ip: Optional[str] = None
    gateway_mac: Optional[str] = None
    gateway_arp_resolved: bool = False
    ping_tests: List[PingResult] = field(default_factory=list)
    dns_tests: List[DnsResult] = field(default_factory=list)
    http_tests: List[HttpResult] = field(default_factory=list)
    internet_connected: bool = False
    overall_status: str = "OK"


@dataclass
class MemoryBenchmarkResult:
    buffer_size_mb: int
    write_speed_mb_s: float
    read_speed_mb_s: float
    integrity_verified: bool
    duration_seconds: float
    error_message: Optional[str] = None
    requested_size_mb: Optional[int] = None
    ram_adjusted: bool = False
    adjustment_reason: Optional[str] = None


@dataclass
class DiskBenchmarkResult:
    target_path: str
    total_size_mb: int
    block_size_kb: int
    write_speed_mb_s: float
    read_speed_mb_s: float
    integrity_verified: bool
    duration_seconds: float
    error_message: Optional[str] = None


@dataclass
class BenchmarkReport:
    memory_benchmark: Optional[MemoryBenchmarkResult] = None
    disk_benchmark: Optional[DiskBenchmarkResult] = None


@dataclass
class DiagnosticReport:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "1.0.0"
    technician_name: Optional[str] = None
    ticket_id: Optional[str] = None
    health_score: int = 100  # 0 to 100
    overall_status: str = "SAUDAVEL"  # "SAUDAVEL", "ATENCAO", "CRITICO"
    system: Optional[SystemInfo] = None
    disk: Optional[DiskReport] = None
    battery: Optional[BatteryReport] = None
    network: Optional[NetworkReport] = None
    benchmark: Optional[BenchmarkReport] = None
    alerts: List[DiagnosticAlert] = field(default_factory=list)
    executive_summary: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Converte a estrutura completa para dicionário puro serializável."""
        return asdict(self)
