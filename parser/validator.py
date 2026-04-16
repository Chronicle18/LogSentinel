from parser.extractor import FieldExtractor
from parser.cim_mapper import CIMMapper
from parser.mitre_mapper import MitreMapper
from configs.loader import SourcetypeConfig
from typing import Dict, Any
import structlog

log = structlog.get_logger()


class Validator:
    def __init__(self, config: SourcetypeConfig):
        self.extractor = FieldExtractor(config)
        self.cim_mapper = CIMMapper(config)
        self.mitre_mapper = MitreMapper()

    def validate_line(self, raw_line: str) -> Dict[str, Any]:
        extracted = self.extractor.extract(raw_line)
        mapped = self.cim_mapper.map_event(extracted, job_id="dry-run")
        tactic = self.mitre_mapper.map_tactics(mapped)
        if tactic:
            mapped["mitre_tactic"] = tactic

        populated = [k for k, v in mapped.items() if v is not None]
        missing = [k for k, v in mapped.items() if v is None]

        required_present = all(mapped.get(f) is not None for f in ["_time", "src", "action"])
        pass_verdict = not mapped.get("parse_error") and required_present

        log.info("validation_result",
                 sourcetype=mapped.get("sourcetype"),
                 verdict="pass" if pass_verdict else "fail",
                 populated_count=len(populated),
                 missing_count=len(missing),
                 parse_error=mapped.get("parse_error"))

        return {
            "populated_fields": populated,
            "missing_fields": missing,
            "pass": pass_verdict,
            "event": mapped
        }
