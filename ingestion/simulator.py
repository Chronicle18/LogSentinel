import os
import random
from datetime import datetime, timedelta
import structlog

log = structlog.get_logger()

def get_random_ip(internal=True):
    if internal:
        return f"10.0.{random.randint(0, 255)}.{random.randint(1, 254)}"
    return f"{random.randint(11, 254)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

def get_random_time(start_time: datetime, max_offset_seconds: int = 86400):
    return start_time + timedelta(seconds=random.randint(0, max_offset_seconds))

def generate_syslog_auth(count=10000, malformed_rate=0.04, attack_patterns=None):
    lines = []
    start_time = datetime.utcnow() - timedelta(days=1)
    
    if attack_patterns:
        for _ in range(12):
            src_ip = get_random_ip(internal=False)
            user = random.choice(["root", "admin", "test", "ubuntu"])
            base_time = get_random_time(start_time)
            for i in range(6): 
                dt = base_time + timedelta(seconds=i*5)
                time_str = dt.strftime("%b %d %H:%M:%S")
                lines.append(f"{time_str} host-01 sshd[{random.randint(1000, 9999)}]: Failed password for {user} from {src_ip}")
    
    users = ["jdoe", "asmith", "root", "admin", "www-data"]
    for _ in range(count):
        if random.random() < malformed_rate:
            lines.append(f"Jan 15 08:23:11 host-01 sshd[123]: Malformed log line without proper formatting")
            continue
            
        dt = get_random_time(start_time)
        time_str = dt.strftime("%b %d %H:%M:%S")
        user = random.choice(users)
        src_ip = get_random_ip()
        
        if random.random() > 0.1:
            lines.append(f"{time_str} host-01 sshd[{random.randint(1000, 9999)}]: Accepted publickey for {user} from {src_ip}")
        else:
            lines.append(f"{time_str} host-01 sshd[{random.randint(1000, 9999)}]: Failed password for invalid user {user} from {src_ip}")
            
    return lines

def generate_syslog_kern(count=10000, malformed_rate=0.04, attack_patterns=None):
    lines = []
    start_time = datetime.utcnow() - timedelta(days=1)
    
    if attack_patterns:
        # Exfiltration
        for _ in range(4):
            dt = get_random_time(start_time)
            time_str = dt.strftime("%b %d %H:%M:%S")
            src_ip = get_random_ip(internal=True)
            dest_ip = get_random_ip(internal=False)
            bytes_out = random.randint(15_000_000, 50_000_000)
            lines.append(f"{time_str} host-01 kernel: [12345.678] fw_traffic: SRC={src_ip} DST={dest_ip} BYTES_OUT={bytes_out}")
            
        # Command & Control
        for _ in range(6):
            dt = get_random_time(start_time)
            time_str = dt.strftime("%b %d %H:%M:%S")
            src_ip = get_random_ip(internal=True)
            dest_ip = get_random_ip(internal=False)
            dest_port = random.choice([4444, 6667, 1337, 8080])
            lines.append(f"{time_str} host-01 kernel: [12345.678] iptables denied: IN=eth0 OUT=eth1 MAC=00 SRC={src_ip} DST={dest_ip} PROTO=TCP SPT={random.randint(1024, 65535)} DPT={dest_port}")
            
    for _ in range(count):
        if random.random() < malformed_rate:
            lines.append("kern.log corrupt line missing timestamp")
            continue
            
        dt = get_random_time(start_time)
        time_str = dt.strftime("%b %d %H:%M:%S")
        if random.random() > 0.3:
            lines.append(f"{time_str} host-01 kernel: [12345.678] INFO generic memory check pass")
        else:
            lines.append(f"{time_str} host-01 kernel: [12345.678] iptables denied: IN=eth0 OUT=eth1 MAC=00 SRC={get_random_ip()} DST={get_random_ip(internal=False)} PROTO=TCP SPT=4544 DPT=80")
    return lines

def generate_winevt_security(count=10000, malformed_rate=0.04, attack_patterns=None):
    lines = []
    start_time = datetime.utcnow() - timedelta(days=1)
    
    if attack_patterns:
        # Lateral Movement
        for _ in range(25):
            dt = get_random_time(start_time)
            time_str = dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:23] + "Z"
            src = f"host-{random.randint(100,200)}"
            dest = get_random_ip(internal=True)
            lines.append(f"{time_str} Host={src} EventID=4624 User=admin Action=logon Target={dest}")
            
    users = ["jdoe", "asmith", "ssytem"]
    for _ in range(count):
        if random.random() < malformed_rate:
            lines.append("Invalid XML formatting for this event.")
            continue
            
        dt = get_random_time(start_time)
        time_str = dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:23] + "Z"
        host = f"host-{random.randint(10, 50)}"
        user = random.choice(users)
        target = get_random_ip(internal=True)
        if random.random() > 0.1:
             lines.append(f"{time_str} Host={host} EventID=4624 User={user} Action=logon Target={target}")
        else:
             lines.append(f"{time_str} Host={host} EventID=4625 User={user} Action=logon_failure Target={target}")
    return lines

def generate_winevt_system(count=10000, malformed_rate=0.04, attack_patterns=None):
    lines = []
    start_time = datetime.utcnow() - timedelta(days=1)
    
    if attack_patterns:
        # Persistence
        for _ in range(6):
            dt = get_random_time(start_time)
            time_str = dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:23] + "Z"
            host = f"host-{random.randint(10, 50)}"
            lines.append(f"{time_str} Host={host} EventID=7045 Action=service_install Severity=INFO Message=A service was installed in the system.")
            
    for _ in range(count):
        if random.random() < malformed_rate:
            lines.append("Missing fields Host=test EventID=")
            continue
            
        dt = get_random_time(start_time)
        time_str = dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:23] + "Z"
        host = f"host-{random.randint(10, 50)}"
        lines.append(f"{time_str} Host={host} EventID=7036 Action=state_change Severity=INFO Message=The Windows Update service entered the running state.")
        
    return lines

def generate_winevt_application(count=10000, malformed_rate=0.04, attack_patterns=None):
    lines = []
    start_time = datetime.utcnow() - timedelta(days=1)
    
    for _ in range(count):
        if random.random() < malformed_rate:
            lines.append("Error format blah")
            continue
            
        dt = get_random_time(start_time)
        time_str = dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:23] + "Z"
        host = f"host-{random.randint(10, 50)}"
        lines.append(f"{time_str} Host={host} EventID=1000 User=system Action=app_start App=chrome.exe")
        
    return lines

def main():
    os.makedirs("data", exist_ok=True)
    
    sa = generate_syslog_auth(10000, attack_patterns=True)
    with open("data/syslog_auth_50k.log", "w") as f:
        f.write("\n".join(sa))
        
    sk = generate_syslog_kern(10000, attack_patterns=True)
    with open("data/syslog_kern_50k.log", "w") as f:
        f.write("\n".join(sk))
        
    ws = generate_winevt_security(10000, attack_patterns=True)
    with open("data/winevt_security_50k.xml", "w") as f:
        f.write("\n".join(ws))
        
    wsy = generate_winevt_system(10000, attack_patterns=True)
    with open("data/winevt_system_50k.xml", "w") as f:
        f.write("\n".join(wsy))
        
    wa = generate_winevt_application(10000, attack_patterns=True)
    with open("data/winevt_application_50k.xml", "w") as f:
        f.write("\n".join(wa))
        
    total = len(sa) + len(sk) + len(ws) + len(wsy) + len(wa)
    log.info("simulation_complete", total_events=total,
             syslog_auth=len(sa), syslog_kern=len(sk),
             winevt_security=len(ws), winevt_system=len(wsy),
             winevt_application=len(wa))

if __name__ == "__main__":
    main()
