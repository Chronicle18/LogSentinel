import pytest
import time
from unittest.mock import patch
from parser.mitre_mapper import MitreMapper
from parser.extractor import FieldExtractor
from parser.cim_mapper import CIMMapper
from configs.loader import ConfigManager
import os


# ---------------------------------------------------------------------------
# Initial Access — stateful 60s window
# ---------------------------------------------------------------------------
class TestInitialAccess:
    def test_triggers_at_threshold(self):
        mapper = MitreMapper()
        for _ in range(4):
            result = mapper.map_tactics({"action": "logon_failure", "src": "10.0.0.5"})
            assert result is None
        result = mapper.map_tactics({"action": "logon_failure", "src": "10.0.0.5"})
        assert result == "Initial Access"

    def test_different_ips_independent(self):
        mapper = MitreMapper()
        for _ in range(4):
            mapper.map_tactics({"action": "logon_failure", "src": "10.0.0.1"})
        mapper.map_tactics({"action": "logon_failure", "src": "10.0.0.2"})
        result = mapper.map_tactics({"action": "logon_failure", "src": "10.0.0.2"})
        assert result is None  # only 2 failures from 10.0.0.2

    def test_continues_after_threshold(self):
        mapper = MitreMapper()
        for _ in range(5):
            mapper.map_tactics({"action": "logon_failure", "src": "10.0.0.5"})
        result = mapper.map_tactics({"action": "logon_failure", "src": "10.0.0.5"})
        assert result == "Initial Access"  # still triggers after 5th

    def test_window_expiry(self):
        mapper = MitreMapper()
        old_time = time.time() - 120  # 2 minutes ago
        mapper.failed_logons["10.0.0.5"] = [old_time] * 4
        result = mapper.map_tactics({"action": "logon_failure", "src": "10.0.0.5"})
        assert result is None  # old entries expired, only 1 recent

    def test_no_src_no_trigger(self):
        mapper = MitreMapper()
        for _ in range(10):
            result = mapper.map_tactics({"action": "logon_failure"})
        assert result is None

    def test_wrong_action_no_trigger(self):
        mapper = MitreMapper()
        for _ in range(10):
            result = mapper.map_tactics({"action": "logon", "src": "10.0.0.5"})
        assert result is None


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
class TestPersistence:
    def test_service_install(self):
        mapper = MitreMapper()
        result = mapper.map_tactics({"action": "service_install"})
        assert "Persistence" in result

    def test_scheduled_task_create(self):
        mapper = MitreMapper()
        result = mapper.map_tactics({"action": "scheduled_task_create"})
        assert "Persistence" in result

    def test_other_action_no_persistence(self):
        mapper = MitreMapper()
        result = mapper.map_tactics({"action": "service_start"})
        assert result is None


# ---------------------------------------------------------------------------
# Lateral Movement
# ---------------------------------------------------------------------------
class TestLateralMovement:
    def test_standard_lateral_movement(self):
        mapper = MitreMapper()
        event = {"action": "logon", "src": "192.168.1.1", "dest": "10.0.0.5"}
        assert mapper.map_tactics(event) == "Lateral Movement"

    def test_same_src_dest_no_trigger(self):
        mapper = MitreMapper()
        event = {"action": "logon", "src": "10.0.0.5", "dest": "10.0.0.5"}
        assert mapper.map_tactics(event) is None

    def test_external_dest_no_trigger(self):
        mapper = MitreMapper()
        event = {"action": "logon", "src": "10.0.0.1", "dest": "8.8.8.8"}
        assert mapper.map_tactics(event) is None

    def test_wrong_action_no_trigger(self):
        mapper = MitreMapper()
        event = {"action": "logon_failure", "src": "192.168.1.1", "dest": "10.0.0.5"}
        assert mapper.map_tactics(event) is None or "Lateral Movement" not in (mapper.map_tactics(event) or "")

    def test_missing_dest_no_trigger(self):
        mapper = MitreMapper()
        event = {"action": "logon", "src": "192.168.1.1"}
        assert mapper.map_tactics(event) is None

    def test_hostname_src_ip_dest(self):
        mapper = MitreMapper()
        event = {"action": "logon", "src": "host-100", "dest": "10.0.0.5"}
        result = mapper.map_tactics(event)
        assert result == "Lateral Movement"


# ---------------------------------------------------------------------------
# Exfiltration
# ---------------------------------------------------------------------------
class TestExfiltration:
    def test_standard_exfiltration(self):
        mapper = MitreMapper()
        event = {"src": "10.0.0.2", "dest": "8.8.8.8", "bytes_out": "15000000"}
        assert mapper.map_tactics(event) == "Exfiltration"

    def test_below_threshold_no_trigger(self):
        mapper = MitreMapper()
        event = {"src": "10.0.0.2", "dest": "8.8.8.8", "bytes_out": "9999999"}
        assert mapper.map_tactics(event) is None

    def test_exact_threshold_no_trigger(self):
        mapper = MitreMapper()
        event = {"src": "10.0.0.2", "dest": "8.8.8.8", "bytes_out": "10000000"}
        assert mapper.map_tactics(event) is None  # > not >=

    def test_internal_dest_no_trigger(self):
        mapper = MitreMapper()
        event = {"src": "10.0.0.2", "dest": "192.168.1.1", "bytes_out": "50000000"}
        assert mapper.map_tactics(event) is None

    def test_integer_bytes_out(self):
        mapper = MitreMapper()
        event = {"src": "10.0.0.2", "dest": "8.8.8.8", "bytes_out": 20000000}
        assert mapper.map_tactics(event) == "Exfiltration"

    def test_missing_dest_no_trigger(self):
        mapper = MitreMapper()
        event = {"src": "10.0.0.2", "bytes_out": "50000000"}
        assert mapper.map_tactics(event) is None


# ---------------------------------------------------------------------------
# Command & Control
# ---------------------------------------------------------------------------
class TestCommandAndControl:
    def test_known_c2_ports(self):
        mapper = MitreMapper()
        for port in [4444, 6667, 1337, 8080]:
            result = mapper.map_tactics({"dest_port": port})
            assert "Command & Control" in result

    def test_normal_port_no_trigger(self):
        mapper = MitreMapper()
        assert mapper.map_tactics({"dest_port": 80}) is None
        assert mapper.map_tactics({"dest_port": 443}) is None
        assert mapper.map_tactics({"dest_port": 22}) is None

    def test_string_port(self):
        mapper = MitreMapper()
        result = mapper.map_tactics({"dest_port": "4444"})
        assert "Command & Control" in result

    def test_no_port_no_trigger(self):
        mapper = MitreMapper()
        assert mapper.map_tactics({"dest_port": None}) is None


# ---------------------------------------------------------------------------
# Multiple tactics
# ---------------------------------------------------------------------------
class TestMultipleTactics:
    def test_persistence_and_c2(self):
        mapper = MitreMapper()
        event = {"action": "service_install", "dest_port": 4444}
        result = mapper.map_tactics(event)
        assert "Persistence" in result
        assert "Command & Control" in result
        assert "," in result

    def test_lateral_and_c2(self):
        mapper = MitreMapper()
        event = {"action": "logon", "src": "192.168.1.1", "dest": "10.0.0.5", "dest_port": 6667}
        result = mapper.map_tactics(event)
        assert "Lateral Movement" in result
        assert "Command & Control" in result


# ---------------------------------------------------------------------------
# Parse error events
# ---------------------------------------------------------------------------
class TestParseErrorEvents:
    def test_parse_error_returns_none(self):
        mapper = MitreMapper()
        assert mapper.map_tactics({"parse_error": True}) is None

    def test_no_tactic_returns_none(self):
        mapper = MitreMapper()
        assert mapper.map_tactics({"action": "app_start", "src": "10.0.0.1"}) is None


# ---------------------------------------------------------------------------
# End-to-end pipeline: raw log → extractor → CIM → MITRE
# ---------------------------------------------------------------------------
class TestEndToEndPipeline:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.cm = ConfigManager(os.path.join(os.path.dirname(__file__), "../configs"))

    def test_syslog_auth_brute_force_triggers_initial_access(self):
        config = self.cm.get_config("syslog_auth")
        extractor = FieldExtractor(config)
        mapper = CIMMapper(config)
        mitre = MitreMapper()

        for i in range(5):
            line = f"Jan 15 08:23:{10+i:02d} host-01 sshd[1234]: Failed password for root from 10.0.0.99"
            extracted = extractor.extract(line)
            mapped = mapper.map_event(extracted, job_id="e2e-test")
            assert mapped["action"] == "logon_failure"
            tactic = mitre.map_tactics(mapped)

        assert tactic == "Initial Access"

    def test_winevt_security_lateral_movement(self):
        config = self.cm.get_config("winevt_security")
        extractor = FieldExtractor(config)
        mapper = CIMMapper(config)
        mitre = MitreMapper()

        line = "2026-01-15T08:23:11.123Z Host=host-200 EventID=4624 User=admin Action=logon Target=10.0.0.5"
        extracted = extractor.extract(line)
        mapped = mapper.map_event(extracted, job_id="e2e-test")
        tactic = mitre.map_tactics(mapped)
        assert tactic == "Lateral Movement"

    def test_syslog_kern_exfiltration(self):
        config = self.cm.get_config("syslog_kern")
        extractor = FieldExtractor(config)
        mapper = CIMMapper(config)
        mitre = MitreMapper()

        line = "Jan 15 08:23:11 host-01 kernel: [12345.678] fw_traffic: SRC=10.0.0.1 DST=203.0.113.5 BYTES_OUT=25000000"
        extracted = extractor.extract(line)
        mapped = mapper.map_event(extracted, job_id="e2e-test")
        tactic = mitre.map_tactics(mapped)
        assert tactic == "Exfiltration"

    def test_syslog_kern_c2(self):
        config = self.cm.get_config("syslog_kern")
        extractor = FieldExtractor(config)
        mapper = CIMMapper(config)
        mitre = MitreMapper()

        line = "Jan 15 08:23:11 host-01 kernel: [12345.678] iptables denied: IN=eth0 OUT=eth1 MAC=00 SRC=10.0.0.1 DST=203.0.113.5 PROTO=TCP SPT=54321 DPT=4444"
        extracted = extractor.extract(line)
        mapped = mapper.map_event(extracted, job_id="e2e-test")
        tactic = mitre.map_tactics(mapped)
        assert "Command & Control" in tactic

    def test_winevt_system_persistence(self):
        config = self.cm.get_config("winevt_system")
        extractor = FieldExtractor(config)
        mapper = CIMMapper(config)
        mitre = MitreMapper()

        line = "2026-02-10T14:00:00.000Z Host=host-02 EventID=7045 Action=service_install Severity=INFO Message=A service was installed."
        extracted = extractor.extract(line)
        mapped = mapper.map_event(extracted, job_id="e2e-test")
        tactic = mitre.map_tactics(mapped)
        assert "Persistence" in tactic

    def test_dead_letter_no_tactic(self):
        config = self.cm.get_config("syslog_auth")
        extractor = FieldExtractor(config)
        mapper = CIMMapper(config)
        mitre = MitreMapper()

        line = "garbage line that matches nothing"
        extracted = extractor.extract(line)
        mapped = mapper.map_event(extracted, job_id="e2e-test")
        tactic = mitre.map_tactics(mapped)
        assert tactic is None
        assert mapped["parse_error"] is True
