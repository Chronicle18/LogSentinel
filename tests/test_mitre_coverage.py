"""MITRE coverage regression test.

Runs the full extractor -> cim_mapper -> mitre_mapper pipeline against the
simulator datasets in ./data/ and asserts every expected ATT&CK tactic fires
at least once. Guards against a class of silent failures where:

  * the simulator stops embedding a pattern,
  * a CIM mapping change breaks the field a MITRE rule depends on,
  * a schema/volume reset wipes validation state (as happened in Phase 4),

without ever failing the unit-level mitre_mapper tests.

This is DB-free: it runs the pipeline in-memory, counts tactics, and asserts.
"""

import os
from collections import Counter

import pytest

from configs.loader import ConfigManager
from ingestion.collector import detect_sourcetype, read_lines
from parser.cim_mapper import CIMMapper
from parser.extractor import FieldExtractor
from parser.mitre_mapper import MitreMapper

DATA_DIR = os.getenv("DATA_DIR", "./data")
CONFIG_DIR = os.getenv("CONFIG_DIR", "./configs")

EXPECTED_TACTICS = {
    "Initial Access",
    "Persistence",
    "Lateral Movement",
    "Command & Control",
    "Exfiltration",
}


def _tactic_counts_from_dataset() -> Counter:
    """Run the full pipeline in-memory and return a Counter of tactic hits."""
    config_manager = ConfigManager(CONFIG_DIR)
    mitre_mapper = MitreMapper()  # shared across files so stateful rules see full stream
    counts: Counter = Counter()

    for filename in sorted(os.listdir(DATA_DIR)):
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.isfile(filepath):
            continue
        if not (filename.endswith(".log") or filename.endswith(".xml")):
            continue

        sourcetype = detect_sourcetype(filepath)
        if not sourcetype:
            continue
        config = config_manager.get_config(sourcetype)
        if not config:
            continue

        extractor = FieldExtractor(config)
        cim_mapper = CIMMapper(config)

        for line in read_lines(filepath):
            extracted = extractor.extract(line)
            mapped = cim_mapper.map_event(extracted, job_id="test")
            tactic = mitre_mapper.map_tactics(mapped)
            if not tactic:
                continue
            # Backend stores multi-tactic hits comma-separated; split to per-tactic.
            for t in tactic.split(","):
                t = t.strip()
                if t:
                    counts[t] += 1

    return counts


@pytest.fixture(scope="module")
def tactic_counts() -> Counter:
    if not os.path.isdir(DATA_DIR) or not os.listdir(DATA_DIR):
        pytest.skip(
            f"No simulator dataset at {DATA_DIR}. "
            f"Run `python -m ingestion.simulator` to generate it."
        )
    return _tactic_counts_from_dataset()


class TestMitreCoverage:
    def test_all_expected_tactics_trigger(self, tactic_counts: Counter):
        """Every one of the 5 v1 tactics must fire at least once in the simulator set."""
        missing = EXPECTED_TACTICS - set(tactic_counts.keys())
        assert not missing, (
            f"MITRE tactics missing from simulator dataset: {sorted(missing)}. "
            f"Got counts: {dict(tactic_counts)}"
        )

    def test_no_unexpected_tactics(self, tactic_counts: Counter):
        """Catches typos or drift — only the 5 canonical v1 tactics should appear."""
        extra = set(tactic_counts.keys()) - EXPECTED_TACTICS
        assert not extra, (
            f"Unexpected MITRE tactic labels in dataset: {sorted(extra)}. "
            f"Either update EXPECTED_TACTICS or fix the mapper."
        )

    @pytest.mark.parametrize(
        "tactic,min_hits",
        [
            ("Initial Access", 10),      # 12 brute-force sequences × threshold
            ("Persistence", 3),          # 5+ service_install events embedded
            ("Lateral Movement", 15),    # 20+ cross-host logons embedded
            ("Command & Control", 3),    # 5+ C2 port connections embedded
            ("Exfiltration", 2),         # 3+ large outbound transfers embedded
        ],
    )
    def test_minimum_hits_per_tactic(
        self, tactic_counts: Counter, tactic: str, min_hits: int
    ):
        """Per-tactic floor matching the attack patterns simulator.py embeds.

        These floors are set below the simulator's embedded counts to tolerate
        rule stateful-window dedup (Initial Access threshold, etc.) while still
        catching a regression that silently drops a tactic to near-zero.
        """
        assert tactic_counts[tactic] >= min_hits, (
            f"{tactic} fired only {tactic_counts[tactic]}× — expected ≥ {min_hits}. "
            f"Check simulator attack patterns and mapper rule."
        )
