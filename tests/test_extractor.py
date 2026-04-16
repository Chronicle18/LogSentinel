import pytest
from configs.loader import ConfigManager
from parser.extractor import FieldExtractor
import os


@pytest.fixture
def config_manager():
    return ConfigManager(os.path.join(os.path.dirname(__file__), "../configs"))


# ---------------------------------------------------------------------------
# syslog_auth — 12 sample lines
# ---------------------------------------------------------------------------
class TestSyslogAuth:
    @pytest.fixture(autouse=True)
    def setup(self, config_manager):
        config = config_manager.get_config("syslog_auth")
        assert config is not None
        self.extractor = FieldExtractor(config)

    def test_login_success_publickey(self):
        line = "Jan 15 08:23:11 host-01 sshd[1234]: Accepted publickey for jdoe from 10.0.0.5"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["user"] == "jdoe"
        assert res["src_ip"] == "10.0.0.5"
        assert res["auth_method"] == "publickey"
        assert res["action"] == "logon"
        assert res["_time"].endswith("Z")

    def test_login_success_password(self):
        line = "Feb  3 14:05:22 webserver sshd[9876]: Accepted password for asmith from 192.168.1.100"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["user"] == "asmith"
        assert res["src_ip"] == "192.168.1.100"
        assert res["auth_method"] == "password"
        assert res["action"] == "logon"

    def test_login_failure_known_user(self):
        line = "Mar 10 22:15:33 host-01 sshd[5555]: Failed password for root from 10.0.0.5"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["user"] == "root"
        assert res["action"] == "logon_failure"

    def test_login_failure_invalid_user(self):
        line = "Apr 12 01:30:00 host-01 sshd[6666]: Failed password for invalid user admin from 172.16.0.1"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["user"] == "admin"
        assert res["src_ip"] == "172.16.0.1"
        assert res["action"] == "logon_failure"

    def test_connection_closed(self):
        line = "May  5 12:00:00 host-01 sshd[7777]: Connection closed by jdoe 10.0.0.5"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["action"] == "Connection closed"
        assert res["user"] == "jdoe"

    def test_malformed_missing_timestamp(self):
        line = "sshd[1234]: Accepted publickey for jdoe from 10.0.0.5"
        res = self.extractor.extract(line)
        assert res["parse_error"] is True
        assert res["raw"] == line

    def test_malformed_truncated(self):
        line = "Jan 15 08:23:11 host-01 sshd[1234]:"
        res = self.extractor.extract(line)
        assert res["parse_error"] is True

    def test_malformed_wrong_daemon(self):
        line = "Jan 15 08:23:11 host-01 httpd[1234]: GET /index.html 200"
        res = self.extractor.extract(line)
        assert res["parse_error"] is True

    def test_malformed_garbage(self):
        line = "Malformed log line without proper formatting"
        res = self.extractor.extract(line)
        assert res["parse_error"] is True
        assert res["raw"] == line

    def test_edge_single_digit_day(self):
        line = "Jun  1 09:00:00 host-01 sshd[1111]: Accepted publickey for www-data from 10.0.0.1"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["user"] == "www-data"

    def test_edge_high_pid(self):
        line = "Dec 31 23:59:59 host-01 sshd[99999]: Failed password for root from 10.255.255.254"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["action"] == "logon_failure"
        assert res["src_ip"] == "10.255.255.254"

    def test_timestamp_normalized_to_utc(self):
        line = "Jan 15 08:23:11 host-01 sshd[1234]: Accepted publickey for jdoe from 10.0.0.5"
        res = self.extractor.extract(line)
        assert res["_time"].endswith("Z")
        assert "T" in res["_time"]


# ---------------------------------------------------------------------------
# syslog_kern — 11 sample lines
# ---------------------------------------------------------------------------
class TestSyslogKern:
    @pytest.fixture(autouse=True)
    def setup(self, config_manager):
        config = config_manager.get_config("syslog_kern")
        assert config is not None
        self.extractor = FieldExtractor(config)

    def test_kernel_error(self):
        line = "Jan 15 08:23:11 host-01 kernel: [12345.678] ERROR oom_kill Out of memory: Killed process 1234"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["severity"] == "ERROR"
        assert res["action"] == "oom_kill"

    def test_kernel_warning(self):
        line = "Feb 20 10:00:00 host-01 kernel: [999.123] WARNING disk_check disk space low"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["severity"] == "WARNING"

    def test_kernel_info(self):
        line = "Mar  5 06:00:00 host-01 kernel: [12345.678] INFO generic memory check pass"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["severity"] == "INFO"

    def test_fw_traffic(self):
        line = "Jan 15 08:23:11 host-01 kernel: [12345.678] fw_traffic: SRC=10.0.0.1 DST=8.8.8.8 BYTES_OUT=1024"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["src_ip"] == "10.0.0.1"
        assert res["dest_ip"] == "8.8.8.8"
        assert res["bytes_out"] == 1024
        assert res["action"] == "fw_traffic"

    def test_fw_traffic_large_bytes(self):
        line = "Apr 10 12:00:00 host-01 kernel: [12345.678] fw_traffic: SRC=10.0.0.2 DST=203.0.113.5 BYTES_OUT=25000000"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["bytes_out"] == 25000000

    def test_iptables_block(self):
        line = "Jan 15 08:23:11 host-01 kernel: [12345.678] iptables denied: IN=eth0 OUT=eth1 MAC=00 SRC=10.0.0.1 DST=203.0.113.5 PROTO=TCP SPT=54321 DPT=4444"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["dest_port"] == 4444
        assert res["src_ip"] == "10.0.0.1"
        assert res["dest_ip"] == "203.0.113.5"
        assert res["action"] == "iptables_denied"

    def test_iptables_block_normal_port(self):
        line = "May 20 15:30:00 host-01 kernel: [12345.678] iptables denied: IN=eth0 OUT=eth1 MAC=00 SRC=10.0.0.3 DST=1.2.3.4 PROTO=TCP SPT=4544 DPT=80"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["dest_port"] == 80

    def test_malformed_corrupt(self):
        line = "kern.log corrupt line missing timestamp"
        res = self.extractor.extract(line)
        assert res["parse_error"] is True

    def test_malformed_partial_fw(self):
        line = "Jan 15 08:23:11 host-01 kernel: [12345.678] fw_traffic: SRC=10.0.0.1"
        res = self.extractor.extract(line)
        assert res["parse_error"] is True

    def test_edge_fatal_severity(self):
        line = "Jun 30 00:00:00 host-01 kernel: [0.001] FATAL panic kernel panic - not syncing"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["severity"] == "FATAL"


# ---------------------------------------------------------------------------
# winevt_security — 11 sample lines
# ---------------------------------------------------------------------------
class TestWinevtSecurity:
    @pytest.fixture(autouse=True)
    def setup(self, config_manager):
        config = config_manager.get_config("winevt_security")
        assert config is not None
        self.extractor = FieldExtractor(config)

    def test_logon_success(self):
        line = "2026-01-15T08:23:11.123Z Host=host-123 EventID=4624 User=admin Action=logon Target=10.0.0.5"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["event_id"] == 4624
        assert res["user"] == "admin"
        assert res["action"] == "logon"
        assert res["target"] == "10.0.0.5"

    def test_logon_failure(self):
        line = "2026-01-15T10:00:00.456Z Host=dc-01 EventID=4625 User=root Action=logon_failure Target=10.0.0.5"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["event_id"] == 4625
        assert res["action"] == "logon_failure"

    def test_logon_without_target(self):
        line = "2026-03-20T12:30:00.789Z Host=workstation-5 EventID=4624 User=jdoe Action=logon"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res.get("target") is None

    def test_timestamp_no_milliseconds(self):
        line = "2026-06-01T09:00:00Z Host=host-01 EventID=4624 User=asmith Action=logon Target=10.0.0.1"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["_time"].endswith("Z")

    def test_timestamp_with_z(self):
        line = "2026-01-15T08:23:11.000Z Host=host-01 EventID=4624 User=test Action=logon Target=192.168.1.1"
        res = self.extractor.extract(line)
        assert not res["parse_error"]

    def test_different_users(self):
        for user in ["jdoe", "SYSTEM", "admin$", "svc_account"]:
            line = f"2026-01-15T08:23:11.123Z Host=host-01 EventID=4624 User={user} Action=logon Target=10.0.0.5"
            res = self.extractor.extract(line)
            assert not res["parse_error"]
            assert res["user"] == user

    def test_malformed_invalid_format(self):
        line = "Invalid XML formatting for this event."
        res = self.extractor.extract(line)
        assert res["parse_error"] is True

    def test_malformed_missing_eventid(self):
        line = "2026-01-15T08:23:11.123Z Host=host-01 User=admin Action=logon"
        res = self.extractor.extract(line)
        assert res["parse_error"] is True

    def test_malformed_empty_line(self):
        line = ""
        res = self.extractor.extract(line)
        assert res["parse_error"] is True

    def test_edge_hostname_with_numbers(self):
        line = "2026-02-28T23:59:59.999Z Host=srv-db-01 EventID=4624 User=dba Action=logon Target=10.10.10.10"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["host"] == "srv-db-01"


# ---------------------------------------------------------------------------
# winevt_system — 11 sample lines
# ---------------------------------------------------------------------------
class TestWinevtSystem:
    @pytest.fixture(autouse=True)
    def setup(self, config_manager):
        config = config_manager.get_config("winevt_system")
        assert config is not None
        self.extractor = FieldExtractor(config)

    def test_service_state_change(self):
        line = "2026-01-15T08:23:11.123Z Host=host-01 EventID=7036 Action=state_change Severity=INFO Message=The Windows Update service entered the running state."
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["event_id"] == 7036
        assert res["action"] == "state_change"
        assert res["severity"] == "INFO"

    def test_service_install(self):
        line = "2026-02-10T14:00:00.000Z Host=host-02 EventID=7045 Action=service_install Severity=INFO Message=A service was installed in the system."
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["action"] == "service_install"

    def test_severity_warning(self):
        line = "2026-03-15T09:30:00.100Z Host=dc-01 EventID=7034 Action=service_crash Severity=WARNING Message=The Print Spooler service terminated unexpectedly."
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["severity"] == "WARNING"

    def test_severity_error(self):
        line = "2026-04-01T00:00:00.500Z Host=host-05 EventID=7031 Action=service_fail Severity=ERROR Message=The DNS Client service terminated unexpectedly."
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["severity"] == "ERROR"

    def test_long_message(self):
        msg = "A" * 500
        line = f"2026-01-01T12:00:00.000Z Host=host-01 EventID=7036 Action=state_change Severity=INFO Message={msg}"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["message"] == msg

    def test_scheduled_task_create(self):
        line = "2026-05-20T16:45:00.000Z Host=host-03 EventID=106 Action=scheduled_task_create Severity=INFO Message=Task scheduler created a new task."
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["action"] == "scheduled_task_create"

    def test_malformed_missing_fields(self):
        line = "Missing fields Host=test EventID="
        res = self.extractor.extract(line)
        assert res["parse_error"] is True

    def test_malformed_no_message(self):
        line = "2026-01-01T12:00:00.000Z Host=host-01 EventID=7036 Action=state_change Severity=INFO"
        res = self.extractor.extract(line)
        assert res["parse_error"] is True

    def test_malformed_garbage(self):
        line = "not a real event line at all"
        res = self.extractor.extract(line)
        assert res["parse_error"] is True

    def test_edge_timestamp_no_millis(self):
        line = "2026-12-31T23:59:59Z Host=host-01 EventID=7036 Action=state_change Severity=INFO Message=Year end service check."
        res = self.extractor.extract(line)
        assert not res["parse_error"]

    def test_edge_hyphenated_host(self):
        line = "2026-06-15T10:00:00.000Z Host=prod-web-srv-01 EventID=7036 Action=state_change Severity=INFO Message=Service running."
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["host"] == "prod-web-srv-01"


# ---------------------------------------------------------------------------
# winevt_application — 11 sample lines
# ---------------------------------------------------------------------------
class TestWinevtApplication:
    @pytest.fixture(autouse=True)
    def setup(self, config_manager):
        config = config_manager.get_config("winevt_application")
        assert config is not None
        self.extractor = FieldExtractor(config)

    def test_app_start(self):
        line = "2026-01-15T08:23:11.123Z Host=host-01 EventID=1000 User=system Action=app_start App=chrome.exe"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["action"] == "app_start"
        assert res["app_name"] == "chrome.exe"
        assert res["user"] == "system"

    def test_app_crash(self):
        line = "2026-02-20T14:30:00.000Z Host=host-02 EventID=1001 User=jdoe Action=app_crash App=outlook.exe"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["action"] == "app_crash"
        assert res["app_name"] == "outlook.exe"

    def test_different_apps(self):
        apps = ["notepad.exe", "explorer.exe", "svchost.exe", "python3.11"]
        for app in apps:
            line = f"2026-01-15T08:23:11.123Z Host=host-01 EventID=1000 User=system Action=app_start App={app}"
            res = self.extractor.extract(line)
            assert not res["parse_error"]
            assert res["app_name"] == app

    def test_different_users(self):
        line = "2026-01-15T08:23:11.123Z Host=host-01 EventID=1000 User=LOCAL_SERVICE Action=app_start App=svchost.exe"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["user"] == "LOCAL_SERVICE"

    def test_high_event_id(self):
        line = "2026-01-15T08:23:11.123Z Host=host-01 EventID=99999 User=system Action=app_error App=java.exe"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["event_id"] == 99999

    def test_malformed_missing_app(self):
        line = "2026-01-15T08:23:11.123Z Host=host-01 EventID=1000 User=system Action=app_start"
        res = self.extractor.extract(line)
        assert res["parse_error"] is True

    def test_malformed_corrupt(self):
        line = "Error format blah"
        res = self.extractor.extract(line)
        assert res["parse_error"] is True

    def test_malformed_partial(self):
        line = "2026-01-15T08:23:11.123Z Host=host-01"
        res = self.extractor.extract(line)
        assert res["parse_error"] is True

    def test_edge_timestamp_no_millis(self):
        line = "2026-07-04T00:00:00Z Host=host-01 EventID=1000 User=system Action=app_start App=test.exe"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["_time"].endswith("Z")

    def test_edge_app_with_version(self):
        line = "2026-01-15T08:23:11.123Z Host=host-01 EventID=1000 User=admin Action=app_install App=node-v18.0.0"
        res = self.extractor.extract(line)
        assert not res["parse_error"]
        assert res["app_name"] == "node-v18.0.0"

    def test_raw_line_preserved(self):
        line = "2026-01-15T08:23:11.123Z Host=host-01 EventID=1000 User=system Action=app_start App=chrome.exe"
        res = self.extractor.extract(line)
        assert res["raw"] == line
