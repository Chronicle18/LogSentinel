from typing import Dict, Any, List
from datetime import datetime
import ipaddress
import time
import structlog

log = structlog.get_logger()

RFC1918_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
]


class MitreMapper:
    def __init__(self):
        self.failed_logons: Dict[str, List[float]] = {}

    def _clean_old_logons(self, current_time: float):
        for ip in list(self.failed_logons.keys()):
            self.failed_logons[ip] = [ts for ts in self.failed_logons[ip] if current_time - ts <= 60]
            if not self.failed_logons[ip]:
                del self.failed_logons[ip]

    def _is_rfc1918(self, ip: str) -> bool:
        if not ip:
            return False
        try:
            addr = ipaddress.ip_address(ip)
            return any(addr in net for net in RFC1918_NETWORKS)
        except ValueError:
            return False

    def map_tactics(self, event: Dict[str, Any]) -> str:
        if event.get("parse_error"):
            return None

        tactics = []
        action = event.get("action")
        src = event.get("src")
        dest = event.get("dest")
        bytes_out = event.get("bytes_out", 0)
        dest_port = event.get("dest_port")
        
        current_ts = time.time()
        
        # 1. Initial Access
        if action == "logon_failure" and src:
            self._clean_old_logons(current_ts)
            if src not in self.failed_logons:
                self.failed_logons[src] = []
            self.failed_logons[src].append(current_ts)
            if len(self.failed_logons[src]) >= 5:
                tactics.append("Initial Access")
                
        # 2. Persistence
        if action in ("service_install", "scheduled_task_create"):
            tactics.append("Persistence")
            
        # 3. Lateral Movement
        if src and dest and src != dest and action == "logon":
            if self._is_rfc1918(dest):
                tactics.append("Lateral Movement")
                
        # 4. Exfiltration
        try:
            bytes_out_val = int(bytes_out) if bytes_out else 0
        except ValueError:
            bytes_out_val = 0
            
        if bytes_out_val > 10_000_000 and dest and not self._is_rfc1918(dest):
            tactics.append("Exfiltration")
            
        # 5. Command & Control
        try:
            dest_port_val = int(dest_port) if dest_port else 0
        except ValueError:
            dest_port_val = 0
            
        if dest_port_val in (4444, 6667, 1337, 8080):
            tactics.append("Command & Control")
            
        if tactics:
            log.info("mitre_tactic_matched", tactics=tactics, src=src, dest=dest, action=action)
            return ",".join(tactics)
            
        return None
