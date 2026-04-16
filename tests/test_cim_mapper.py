import pytest
from configs.loader import ConfigManager
from parser.extractor import FieldExtractor
from parser.cim_mapper import CIMMapper, SEVERITY_NORMALIZE
import os


@pytest.fixture
def config_manager():
    return ConfigManager(os.path.join(os.path.dirname(__file__), "../configs"))


REQUIRED_CIM_FIELDS = [
    "_time", "src", "dest", "user", "action",
    "severity", "sourcetype", "raw", "parse_error", "job_id"
]


# ---------------------------------------------------------------------------
# syslog_auth CIM mapping
# ---------------------------------------------------------------------------
class TestCIMSyslogAuth:
    @pytest.fixture(autouse=True)
    def setup(self, config_manager):
        config = config_manager.get_config("syslog_auth")
        self.extractor = FieldExtractor(config)
        self.mapper = CIMMapper(config)

    def test_all_required_fields_present(self):
        line = "Jan 15 08:23:11 host-01 sshd[1234]: Accepted publickey for jdoe from 10.0.0.5"
        extracted = self.extractor.extract(line)
        mapped = self.mapper.map_event(extracted, job_id="test-001")
        for field in REQUIRED_CIM_FIELDS:
            assert field in mapped, f"Missing CIM field: {field}"

    def test_field_mapping_success(self):
        line = "Jan 15 08:23:11 host-01 sshd[1234]: Accepted publickey for jdoe from 10.0.0.5"
        extracted = self.extractor.extract(line)
        mapped = self.mapper.map_event(extracted, job_id="test-001")
        assert mapped["src"] == "10.0.0.5"
        assert mapped["action"] == "logon"
        assert mapped["user"] == "jdoe"
        assert mapped["severity"] == "medium"
        assert mapped["job_id"] == "test-001"

    def test_field_mapping_failure(self):
        line = "Mar 10 22:15:33 host-01 sshd[5555]: Failed password for root from 10.0.0.5"
        extracted = self.extractor.extract(line)
        mapped = self.mapper.map_event(extracted, job_id="test-002")
        assert mapped["action"] == "logon_failure"
        assert mapped["user"] == "root"

    def test_dead_letter_preserves_raw(self):
        line = "Random unparseable log"
        extracted = self.extractor.extract(line)
        mapped = self.mapper.map_event(extracted, job_id="test-003")
        assert mapped["parse_error"] is True
        assert mapped["raw"] == line
        assert mapped["job_id"] == "test-003"

    def test_matched_rule_stripped(self):
        line = "Jan 15 08:23:11 host-01 sshd[1234]: Accepted publickey for jdoe from 10.0.0.5"
        extracted = self.extractor.extract(line)
        assert "_matched_rule" in extracted
        mapped = self.mapper.map_event(extracted, job_id="test-001")
        assert "_matched_rule" not in mapped

    def test_default_job_id_generated(self):
        line = "Jan 15 08:23:11 host-01 sshd[1234]: Accepted publickey for jdoe from 10.0.0.5"
        extracted = self.extractor.extract(line)
        mapped = self.mapper.map_event(extracted)
        assert mapped["job_id"] is not None
        assert len(mapped["job_id"]) > 0


# ---------------------------------------------------------------------------
# syslog_kern CIM mapping
# ---------------------------------------------------------------------------
class TestCIMSyslogKern:
    @pytest.fixture(autouse=True)
    def setup(self, config_manager):
        config = config_manager.get_config("syslog_kern")
        self.extractor = FieldExtractor(config)
        self.mapper = CIMMapper(config)

    def test_fw_traffic_mapping(self):
        line = "Jan 15 08:23:11 host-01 kernel: [12345.678] fw_traffic: SRC=10.0.0.1 DST=8.8.8.8 BYTES_OUT=1024"
        extracted = self.extractor.extract(line)
        mapped = self.mapper.map_event(extracted, job_id="test-k1")
        assert mapped["src"] == "10.0.0.1"
        assert mapped["dest"] == "8.8.8.8"
        assert mapped["action"] == "fw_traffic"

    def test_iptables_mapping(self):
        line = "Jan 15 08:23:11 host-01 kernel: [12345.678] iptables denied: IN=eth0 OUT=eth1 MAC=00 SRC=10.0.0.1 DST=203.0.113.5 PROTO=TCP SPT=54321 DPT=4444"
        extracted = self.extractor.extract(line)
        mapped = self.mapper.map_event(extracted, job_id="test-k2")
        assert mapped["src"] == "10.0.0.1"
        assert mapped["dest"] == "203.0.113.5"
        assert mapped["action"] == "iptables_denied"

    def test_default_severity_low(self):
        line = "Jan 15 08:23:11 host-01 kernel: [12345.678] fw_traffic: SRC=10.0.0.1 DST=8.8.8.8 BYTES_OUT=1024"
        extracted = self.extractor.extract(line)
        mapped = self.mapper.map_event(extracted, job_id="test-k3")
        assert mapped["severity"] == "low"


# ---------------------------------------------------------------------------
# winevt_security CIM mapping
# ---------------------------------------------------------------------------
class TestCIMWinevtSecurity:
    @pytest.fixture(autouse=True)
    def setup(self, config_manager):
        config = config_manager.get_config("winevt_security")
        self.extractor = FieldExtractor(config)
        self.mapper = CIMMapper(config)

    def test_logon_mapping(self):
        line = "2026-01-15T08:23:11.123Z Host=host-01 EventID=4624 User=admin Action=logon Target=10.0.0.5"
        extracted = self.extractor.extract(line)
        mapped = self.mapper.map_event(extracted, job_id="test-ws1")
        assert mapped["src"] == "host-01"
        assert mapped["dest"] == "10.0.0.5"
        assert mapped["action"] == "logon"

    def test_missing_target_is_none(self):
        line = "2026-03-20T12:30:00.789Z Host=workstation-5 EventID=4624 User=jdoe Action=logon"
        extracted = self.extractor.extract(line)
        mapped = self.mapper.map_event(extracted, job_id="test-ws2")
        assert mapped["dest"] is None


# ---------------------------------------------------------------------------
# winevt_system CIM mapping + severity normalization
# ---------------------------------------------------------------------------
class TestCIMWinevtSystem:
    @pytest.fixture(autouse=True)
    def setup(self, config_manager):
        config = config_manager.get_config("winevt_system")
        self.extractor = FieldExtractor(config)
        self.mapper = CIMMapper(config)

    def test_severity_info_normalized_to_low(self):
        line = "2026-01-15T08:23:11.123Z Host=host-01 EventID=7036 Action=state_change Severity=INFO Message=Running."
        extracted = self.extractor.extract(line)
        mapped = self.mapper.map_event(extracted, job_id="test-sys1")
        assert mapped["severity"] == "low"

    def test_severity_warning_normalized_to_medium(self):
        line = "2026-03-15T09:30:00.100Z Host=dc-01 EventID=7034 Action=service_crash Severity=WARNING Message=Crashed."
        extracted = self.extractor.extract(line)
        mapped = self.mapper.map_event(extracted, job_id="test-sys2")
        assert mapped["severity"] == "medium"

    def test_severity_error_normalized_to_high(self):
        line = "2026-04-01T00:00:00.500Z Host=host-05 EventID=7031 Action=service_fail Severity=ERROR Message=Failed."
        extracted = self.extractor.extract(line)
        mapped = self.mapper.map_event(extracted, job_id="test-sys3")
        assert mapped["severity"] == "high"

    def test_host_mapped_to_src(self):
        line = "2026-01-15T08:23:11.123Z Host=host-01 EventID=7036 Action=state_change Severity=INFO Message=Running."
        extracted = self.extractor.extract(line)
        mapped = self.mapper.map_event(extracted, job_id="test-sys4")
        assert mapped["src"] == "host-01"


# ---------------------------------------------------------------------------
# winevt_application CIM mapping
# ---------------------------------------------------------------------------
class TestCIMWinevtApplication:
    @pytest.fixture(autouse=True)
    def setup(self, config_manager):
        config = config_manager.get_config("winevt_application")
        self.extractor = FieldExtractor(config)
        self.mapper = CIMMapper(config)

    def test_app_event_mapping(self):
        line = "2026-01-15T08:23:11.123Z Host=host-01 EventID=1000 User=system Action=app_start App=chrome.exe"
        extracted = self.extractor.extract(line)
        mapped = self.mapper.map_event(extracted, job_id="test-app1")
        assert mapped["src"] == "host-01"
        assert mapped["action"] == "app_start"
        assert mapped["user"] == "system"
        assert mapped["severity"] == "low"

    def test_all_required_fields(self):
        line = "2026-01-15T08:23:11.123Z Host=host-01 EventID=1000 User=system Action=app_start App=chrome.exe"
        extracted = self.extractor.extract(line)
        mapped = self.mapper.map_event(extracted, job_id="test-app2")
        for field in REQUIRED_CIM_FIELDS:
            assert field in mapped, f"Missing CIM field: {field}"


# ---------------------------------------------------------------------------
# Severity normalization unit tests
# ---------------------------------------------------------------------------
class TestSeverityNormalization:
    @pytest.fixture(autouse=True)
    def setup(self, config_manager):
        config = config_manager.get_config("syslog_auth")
        self.mapper = CIMMapper(config)

    def test_valid_cim_values_pass_through(self):
        for val in ["low", "medium", "high", "critical"]:
            assert self.mapper._normalize_severity(val) == val

    def test_common_log_levels_normalized(self):
        assert self.mapper._normalize_severity("INFO") == "low"
        assert self.mapper._normalize_severity("WARNING") == "medium"
        assert self.mapper._normalize_severity("ERROR") == "high"
        assert self.mapper._normalize_severity("FATAL") == "critical"

    def test_case_insensitive(self):
        assert self.mapper._normalize_severity("info") == "low"
        assert self.mapper._normalize_severity("Warning") == "medium"
        assert self.mapper._normalize_severity("error") == "high"

    def test_unknown_falls_back_to_default(self):
        result = self.mapper._normalize_severity("UNKNOWN_LEVEL")
        assert result == "medium"  # syslog_auth default_severity

    def test_none_falls_back_to_default(self):
        result = self.mapper._normalize_severity(None)
        assert result == "medium"

    def test_empty_string_falls_back_to_default(self):
        result = self.mapper._normalize_severity("")
        assert result == "medium"
