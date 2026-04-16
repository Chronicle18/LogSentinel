import re
import ipaddress
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import structlog
from configs.loader import SourcetypeConfig

log = structlog.get_logger()

class FieldExtractor:
    def __init__(self, config: SourcetypeConfig):
        self.config = config
        self.compiled_rules = []
        for rule in config.transforms:
            try:
                compiled = re.compile(rule.pattern)
                self.compiled_rules.append((rule, compiled))
            except re.error as e:
                log.error("regex_compile_error", rule=rule.name, error=str(e))

    def _normalize_time(self, raw_time: str, time_format: str) -> Optional[str]:
        try:
            if raw_time.endswith("Z"):
                raw_time = raw_time[:-1]
            if "%f" in time_format and "." not in raw_time:
                time_format = time_format.replace(".%f", "")
                
            dt = datetime.strptime(raw_time, time_format)
            if "%Y" not in time_format and "%y" not in time_format:
                dt = dt.replace(year=datetime.now(timezone.utc).year)
            return dt.isoformat() + "Z"
        except ValueError as e:
            log.warning("time_normalization_error", raw_time=raw_time, error=str(e))
            return None

    def _validate_types(self, match_dict: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        for k, v in match_dict.items():
            if v is None:
                continue
                
            if "ip" in k.lower() or k in ("src", "dest", "src_ip", "dest_ip"):
                try:
                    ipaddress.ip_address(v)
                    result[k] = str(v)
                except ValueError:
                    log.warning("invalid_ip", field=k, value=v)
                    result[k] = str(v)
            elif "port" in k.lower() or "count" in k.lower() or "bytes" in k.lower() or k == "event_id":
                try:
                    result[k] = int(v)
                except ValueError:
                    log.warning("invalid_integer", field=k, value=v)
                    result[k] = v
            else:
                result[k] = str(v)
        return result

    def extract(self, raw_line: str) -> Dict[str, Any]:
        match_dict = None
        matched_rule = None

        for rule, compiled in self.compiled_rules:
            match = compiled.match(raw_line) or compiled.search(raw_line)
            if match:
                match_dict = match.groupdict()
                matched_rule = rule.name
                break
                
        if not match_dict:
            log.warning("parse_error", sourcetype=self.config.sourcetype, raw_line=raw_line[:200])
            return {
                "raw": raw_line,
                "parse_error": True,
                "sourcetype": self.config.sourcetype,
                "_matched_rule": None
            }

        extracted = self._validate_types(match_dict)

        for rule, _ in self.compiled_rules:
            if rule.name == matched_rule and rule.static_fields:
                extracted.update(rule.static_fields)
                break

        if "_time" in extracted:
            normalized_time = self._normalize_time(extracted["_time"], self.config.time_format)
            if normalized_time:
                extracted["_time"] = normalized_time

        extracted["raw"] = raw_line
        extracted["parse_error"] = False
        extracted["sourcetype"] = self.config.sourcetype
        extracted["_matched_rule"] = matched_rule
        return extracted
