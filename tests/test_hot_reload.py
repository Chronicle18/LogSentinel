"""Hot-reload regression test.

CLAUDE.md §6 makes hot-reload a hard requirement: ConfigManager uses watchdog
to pick up YAML changes without a server restart. This test validates that
end-to-end by:

  1. Starting a ConfigManager watching a temp directory with a minimal config
  2. Running an extractor against a line — assert the v1 rule matches
  3. Rewriting the YAML on disk with a rule that tags an *additional* field
  4. Waiting briefly for watchdog to fire
  5. Re-running extraction — assert the v2 rule took effect without restart

A passing run proves that a config change in production doesn't require a
bounce.
"""

import time
from pathlib import Path

import pytest

from configs.loader import ConfigManager
from parser.extractor import FieldExtractor


V1_CONFIG = """\
sourcetype: hotreload_probe
time_format: "%Y-%m-%d %H:%M:%S"
transforms:
  - name: v1_rule
    pattern: "^user=(?P<user>\\\\w+) action=(?P<action>\\\\w+)$"
    fields: [user, action]
cim_mapping:
  user: user
  action: action
default_severity: low
"""

V2_CONFIG = """\
sourcetype: hotreload_probe
time_format: "%Y-%m-%d %H:%M:%S"
transforms:
  - name: v2_rule
    pattern: "^user=(?P<user>\\\\w+) action=(?P<action>\\\\w+) src=(?P<src>\\\\S+)$"
    fields: [user, action, src]
cim_mapping:
  user: user
  action: action
  src: src
default_severity: low
"""


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    d = tmp_path / "configs"
    d.mkdir()
    (d / "hotreload_probe.yaml").write_text(V1_CONFIG)
    return d


def _wait_for(predicate, timeout: float = 5.0, interval: float = 0.1) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


class TestHotReload:
    def test_yaml_change_propagates_without_restart(self, config_dir: Path):
        manager = ConfigManager(str(config_dir))
        manager.start_watching()
        try:
            # v1 rule: only matches lines without src.
            config = manager.get_config("hotreload_probe")
            assert config is not None, "initial config should load"
            assert config.transforms[0].name == "v1_rule"

            extractor_v1 = FieldExtractor(config)
            with_src = "user=alice action=login src=10.0.0.5"
            v1_result = extractor_v1.extract(with_src)
            assert v1_result.get("parse_error") is True, (
                "v1 rule must NOT match the longer line (regex anchored)"
            )

            # Rewrite YAML on disk; watchdog should pick it up.
            (config_dir / "hotreload_probe.yaml").write_text(V2_CONFIG)

            # Wait for reload — poll the config for the new rule name.
            reloaded = _wait_for(
                lambda: (
                    manager.get_config("hotreload_probe")
                    and manager.get_config("hotreload_probe").transforms[0].name
                    == "v2_rule"
                ),
                timeout=5.0,
            )
            assert reloaded, (
                "ConfigManager did not pick up YAML change within 5s — "
                "watchdog reload is broken."
            )

            # v2 rule matches the same line and extracts src.
            new_config = manager.get_config("hotreload_probe")
            extractor_v2 = FieldExtractor(new_config)
            v2_result = extractor_v2.extract(with_src)
            assert v2_result.get("parse_error") is not True, v2_result
            assert v2_result.get("user") == "alice"
            assert v2_result.get("action") == "login"
            assert v2_result.get("src") == "10.0.0.5"
        finally:
            manager.stop_watching()

    def test_new_yaml_file_is_picked_up(self, config_dir: Path):
        manager = ConfigManager(str(config_dir))
        manager.start_watching()
        try:
            assert manager.get_config("latecomer") is None

            new_yaml = V1_CONFIG.replace("hotreload_probe", "latecomer")
            (config_dir / "latecomer.yaml").write_text(new_yaml)

            appeared = _wait_for(
                lambda: manager.get_config("latecomer") is not None,
                timeout=5.0,
            )
            assert appeared, "New YAML file was not picked up by the watcher."
        finally:
            manager.stop_watching()
