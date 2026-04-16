from typing import Dict, Any
from configs.loader import SourcetypeConfig
import uuid
import structlog

log = structlog.get_logger()

SEVERITY_NORMALIZE = {
    "info": "low",
    "information": "low",
    "warning": "medium",
    "warn": "medium",
    "error": "high",
    "err": "high",
    "fatal": "critical",
    "critical": "critical",
    "low": "low",
    "medium": "medium",
    "high": "high",
}


class CIMMapper:
    def __init__(self, config: SourcetypeConfig):
        self.config = config
        self.required_fields = [
            "_time", "src", "dest", "user", "action",
            "severity", "sourcetype", "raw", "parse_error", "job_id"
        ]

    def map_event(self, extracted: Dict[str, Any], job_id: str = None) -> Dict[str, Any]:
        if not job_id:
            job_id = str(uuid.uuid4())

        if extracted.get("parse_error"):
            return self._ensure_required(extracted, job_id)

        mapped = extracted.copy()

        for ext_field, cim_field in self.config.cim_mapping.items():
            if ext_field in mapped:
                mapped[cim_field] = mapped.pop(ext_field)

        if "severity" not in mapped or mapped["severity"] is None:
            mapped["severity"] = self.config.default_severity

        mapped["severity"] = self._normalize_severity(mapped["severity"])

        return self._ensure_required(mapped, job_id)

    def _normalize_severity(self, raw_severity: str) -> str:
        if not raw_severity:
            return self.config.default_severity
        normalized = SEVERITY_NORMALIZE.get(raw_severity.lower())
        if normalized:
            return normalized
        log.warning("unknown_severity_value", raw=raw_severity,
                    fallback=self.config.default_severity,
                    sourcetype=self.config.sourcetype)
        return self.config.default_severity

    def _ensure_required(self, data: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        data["job_id"] = job_id
        data.pop("_matched_rule", None)
        for field in self.required_fields:
            if field not in data:
                data[field] = None
        return data
