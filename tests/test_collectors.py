"""
Testes unitários para os coletores de dados e avaliação de saúde do PenDiag.
"""

import unittest
from unittest.mock import patch, MagicMock
from pendiag.collectors.system import collect_system_info
from pendiag.collectors.disk import collect_disk_report
from pendiag.collectors.battery import collect_battery_report
from pendiag.collectors.network import collect_network_report
from pendiag.utils import evaluate_health, generate_executive_summary
from pendiag.models import (
    DiagnosticReport,
    NetworkReport,
    PingResult,
    DnsResult,
    HttpResult,
    SystemInfo,
    DiskReport,
    BatteryReport
)


class TestCollectors(unittest.TestCase):

    def test_collect_system_info(self):
        info = collect_system_info()
        self.assertIsNotNone(info.hostname)
        self.assertIsNotNone(info.os_name)
        self.assertGreater(info.ram_total_bytes, 0)
        self.assertGreater(info.cpu_logical_cores, 0)
        self.assertTrue(0.0 <= info.ram_usage_percent <= 100.0)
        # Novos campos presentes
        self.assertTrue(hasattr(info, "antivirus_name"))
        self.assertTrue(hasattr(info, "antivirus_enabled"))
        self.assertTrue(hasattr(info, "antivirus_updated"))
        self.assertTrue(hasattr(info, "cpu_temperature_c"))

    def test_collect_disk_report(self):
        report = collect_disk_report()
        self.assertIsNotNone(report.overall_health)
        self.assertIn(report.overall_health, ["OK", "WARNING", "CRITICAL"])
        self.assertGreaterEqual(len(report.partitions), 1)
        if report.disks:
            d = report.disks[0]
            self.assertTrue(hasattr(d, "temperature_c"))
            self.assertTrue(hasattr(d, "wear_percent"))
            self.assertTrue(hasattr(d, "spindle_speed_rpm"))
            self.assertTrue(hasattr(d, "allocated_size_bytes"))

    def test_collect_battery_report(self):
        report = collect_battery_report()
        self.assertIsNotNone(report.present)
        if report.present:
            self.assertIsNotNone(report.percent)
            self.assertTrue(0.0 <= report.percent <= 100.0)

    def test_collect_network_report(self):
        report = collect_network_report()
        self.assertIsNotNone(report.overall_status)
        self.assertIsInstance(report.interfaces, list)
        self.assertIsInstance(report.ping_tests, list)
        self.assertIsInstance(report.dns_tests, list)
        self.assertTrue(hasattr(report, "gateway_arp_resolved"))
        self.assertTrue(hasattr(report, "gateway_mac"))

    def test_evaluate_health_gateway_firewall_ignored_when_wan_ok(self):
        """
        Cenário: Gateway local (192.168.0.1) bloqueia ping (100% loss),
        mas o acesso WAN à internet está 100% funcional (1.1.1.1 0% loss, DNS ok).
        O score NÃO deve ser penalizado como rede instável/offline.
        """
        rep = DiagnosticReport()
        rep.system = SystemInfo(
            hostname="test", os_name="Linux", os_version="1.0", os_release="1.0",
            architecture="x86_64", boot_time="", uptime_human="", cpu_model="Test CPU",
            cpu_physical_cores=4, cpu_logical_cores=8, cpu_freq_current_mhz=2000.0,
            cpu_freq_max_mhz=3000.0, cpu_usage_percent=20.0, ram_total_bytes=16*1024**3,
            ram_used_bytes=4*1024**3, ram_free_bytes=12*1024**3, ram_usage_percent=25.0,
            swap_total_bytes=4*1024**3, swap_used_bytes=0, swap_usage_percent=0.0
        )
        rep.disk = DiskReport()
        rep.battery = BatteryReport(present=False)

        rep.network = NetworkReport(
            gateway_ip="192.168.0.1",
            gateway_mac="58-d9-d5-a7-e1-40",
            gateway_arp_resolved=True,
            internet_connected=True,
            ping_tests=[
                PingResult(target="192.168.0.1", packets_sent=2, packets_received=0,
                           packet_loss_percent=100.0, min_rtt_ms=None, avg_rtt_ms=None,
                           max_rtt_ms=None, success=False, status="INACESSIVEL"),
                PingResult(target="1.1.1.1", packets_sent=2, packets_received=2,
                           packet_loss_percent=0.0, min_rtt_ms=20.0, avg_rtt_ms=22.0,
                           max_rtt_ms=25.0, success=True, status="OK"),
            ],
            dns_tests=[
                DnsResult(domain="cloudflare.com", dns_server="1.1.1.1",
                          resolved_ip="104.16.132.229", latency_ms=15.0, success=True)
            ]
        )

        score, status, alerts = evaluate_health(rep)

        # O score deve permanecer 100 (saudável) e status SAUDAVEL
        self.assertEqual(score, 100)
        self.assertEqual(status, "SAUDAVEL")
        
        # Não deve haver alertas CRITICAL ou WARNING para REDE
        network_warnings = [a for a in alerts if a.category == "REDE" and a.level in ["WARNING", "CRITICAL"]]
        self.assertEqual(len(network_warnings), 0)

        # Deve haver apenas alerta INFO explicando o firewall do gateway
        gw_infos = [a for a in alerts if a.category == "REDE" and a.level == "INFO"]
        self.assertGreaterEqual(len(gw_infos), 1)

    def test_evaluate_health_real_network_failure(self):
        """
        Cenário: Falha real de conexão (sem internet).
        O score deve ser devidamente penalizado com status ATENCAO/CRITICO.
        """
        rep = DiagnosticReport()
        rep.system = SystemInfo(
            hostname="test", os_name="Linux", os_version="1.0", os_release="1.0",
            architecture="x86_64", boot_time="", uptime_human="", cpu_model="Test CPU",
            cpu_physical_cores=4, cpu_logical_cores=8, cpu_freq_current_mhz=2000.0,
            cpu_freq_max_mhz=3000.0, cpu_usage_percent=20.0, ram_total_bytes=16*1024**3,
            ram_used_bytes=4*1024**3, ram_free_bytes=12*1024**3, ram_usage_percent=25.0,
            swap_total_bytes=4*1024**3, swap_used_bytes=0, swap_usage_percent=0.0
        )
        rep.disk = DiskReport()
        rep.battery = BatteryReport(present=False)

        rep.network = NetworkReport(
            gateway_ip="192.168.0.1",
            internet_connected=False,
            ping_tests=[
                PingResult(target="192.168.0.1", packets_sent=2, packets_received=0,
                           packet_loss_percent=100.0, min_rtt_ms=None, avg_rtt_ms=None,
                           max_rtt_ms=None, success=False, status="INACESSIVEL"),
                PingResult(target="1.1.1.1", packets_sent=2, packets_received=0,
                           packet_loss_percent=100.0, min_rtt_ms=None, avg_rtt_ms=None,
                           max_rtt_ms=None, success=False, status="INACESSIVEL"),
            ],
            dns_tests=[
                DnsResult(domain="cloudflare.com", dns_server="1.1.1.1",
                          resolved_ip=None, latency_ms=None, success=False, error="Timeout")
            ]
        )

        score, status, alerts = evaluate_health(rep)
        self.assertLess(score, 100)
        network_alerts = [a for a in alerts if a.category == "REDE"]
        self.assertGreaterEqual(len(network_alerts), 1)

    def test_executive_summary_generation(self):
        rep = DiagnosticReport()
        rep.system = collect_system_info()
        rep.disk = collect_disk_report()
        rep.battery = collect_battery_report()
        rep.network = collect_network_report()

        score, status, alerts = evaluate_health(rep)
        rep.health_score = score
        rep.overall_status = status
        rep.alerts = alerts

        summary = generate_executive_summary(rep)
        self.assertIsInstance(summary, list)
        self.assertGreater(len(summary), 0)
        for item in summary:
            self.assertIsInstance(item, str)
            self.assertGreater(len(item), 10)


if __name__ == "__main__":
    unittest.main()
