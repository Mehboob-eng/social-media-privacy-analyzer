import subprocess
import threading
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
import tkinter as tk
from tkinter import messagebox

import requests  # pip install requests


# ============== CONFIG ==============

# Interface name (use your list_interfaces code to find it)
INTERFACE = "Wi-Fi"   # change to your actual interface name

# Hosts we care about (SNI hostnames)
MONITORED_HOSTS = {
    "gateway.facebook.com",
    "static.xx.fbcdn.net",
    "www.facebook.com",
    "instagram.com",
    "www.instagram.com",
    "twitter.com",
    "www.twitter.com",
    "x.com",
    "www.x.com",
    "linkedin.com",
    "www.linkedin.com",
}

# Django server endpoint (placeholder)
API_URL = "http://localhost:8000/api/packets/"   # change to your real endpoint
API_JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY1NjIyMzM3LCJpYXQiOjE3NjU2MjIwMzcsImp0aSI6IjYxYzIxMzQ5ODhlMjRkMWE4OGYwY2U5YTI1MGQ2Y2I4IiwidXNlcl9pZCI6IjEyIn0.j7R4oAI5OvJoqk9hF0XLgPbWZI6NwITyqu_seDAHerI"                 # put your JWT here


# ============== DATA MODEL ==============

@dataclass
class Connection:
    src_ip: str
    src_port: int
    dst_ip: str
    dst_port: int
    hostname: str

    def key(self) -> Tuple[Tuple[str, int], Tuple[str, int]]:
        """
        Normalized key: ( (ip_a, port_a), (ip_b, port_b) ) sorted.
        This way, A→B and B→A are the same connection.
        """
        a = (self.src_ip, self.src_port)
        b = (self.dst_ip, self.dst_port)
        return (a, b) if a <= b else (b, a)


def make_key(ip1: str, port1: int, ip2: str, port2: int) -> Tuple[Tuple[str, int], Tuple[str, int]]:
    a = (ip1, port1)
    b = (ip2, port2)
    return (a, b) if a <= b else (b, a)


# ============== GLOBAL STATE ==============

# 1) All currently active monitored connections
active_connections: Dict[Tuple[Tuple[str, int], Tuple[str, int]], Connection] = {}

# 2) Threads that process packets per connection
packet_threads: Dict[Tuple[Tuple[str, int], Tuple[str, int]], threading.Thread] = {}

# One lock to protect active_connections + packet_threads
state_lock = threading.Lock()


# ============== FUNCTION 1: CONNECTION MONITOR ==============

def handshake_worker():
    """
    1) Runs continuously.
    2) Listens for TLS ClientHello (start of HTTPS).
    3) If hostname is one of FB/IG/Twitter/LinkedIn, add Connection to active_connections.
    """

    tshark_cmd = [
        "tshark",
        "-l",
        "-i", INTERFACE,
        "-Y", "tls.handshake.type == 1",  # TLS ClientHello
        "-T", "fields",
        "-e", "ip.src",
        "-e", "tcp.srcport",
        "-e", "ip.dst",
        "-e", "tcp.dstport",
        "-e", "tls.handshake.extensions_server_name",
    ]

    proc = subprocess.Popen(
        tshark_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )

    print("[HANDSHAKE] Listening for TLS handshakes on", INTERFACE)

    try:
        while True:
            line = proc.stdout.readline()
            if not line:
                break

            line = line.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) < 4:
                continue

            src_ip, src_port_str, dst_ip, dst_port_str = parts[0:4]
            hostname = parts[4] if len(parts) >= 5 else ""

            try:
                src_port = int(src_port_str)
                dst_port = int(dst_port_str)
            except ValueError:
                continue

            # Filter only the social hosts we care about
            if hostname not in MONITORED_HOSTS:
                continue

            conn = Connection(
                src_ip=src_ip,
                src_port=src_port,
                dst_ip=dst_ip,
                dst_port=dst_port,
                hostname=hostname,
            )
            key = conn.key()

            with state_lock:
                if key not in active_connections:
                    active_connections[key] = conn
                    print(f"[NEW] {src_ip}:{src_port} -> {dst_ip}:{dst_port} host={hostname}")
    finally:
        proc.terminate()
        print("[HANDSHAKE] Worker stopped")


def end_worker():
    """
    1) Runs continuously.
    2) Listens for TCP FIN / RST.
    3) If a connection key exists in active_connections, remove it.
    """

    tshark_cmd = [
        "tshark",
        "-l",
        "-i", INTERFACE,
        "-Y", "tcp.flags.fin==1 or tcp.flags.reset==1",
        "-T", "fields",
        "-e", "ip.src",
        "-e", "tcp.srcport",
        "-e", "ip.dst",
        "-e", "tcp.dstport",
    ]

    proc = subprocess.Popen(
        tshark_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )

    print("[END] Listening for TCP FIN/RST on", INTERFACE)

    try:
        while True:
            line = proc.stdout.readline()
            if not line:
                break

            line = line.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) < 4:
                continue

            src_ip, src_port_str, dst_ip, dst_port_str = parts[0:4]

            try:
                src_port = int(src_port_str)
                dst_port = int(dst_port_str)
            except ValueError:
                continue

            key = make_key(src_ip, src_port, dst_ip, dst_port)

            with state_lock:
                removed_conn = active_connections.pop(key, None)
                if removed_conn is not None:
                    print(f"[END] {src_ip}:{src_port} <-> {dst_ip}:{dst_port} host={removed_conn.hostname}")

                # When connection ends, its packet thread will see that it disappeared and stop
    finally:
        proc.terminate()
        print("[END] Worker stopped")


# ============== FUNCTION 3: SPAM DETECTION + SEND TO SERVER ==============

def is_packet_spam(conn: Connection, packet_line: str) -> bool:
    """
    Simple placeholder spam detection.
    For now:
      - If hostname is not in MONITORED_HOSTS → treat as suspicious/spam
      - Later you will add rate checks, patterns, etc.
    """
    if conn.hostname not in MONITORED_HOSTS and conn.dst_port == 443:
        return True

    messagebox.showwarning("SPAM DETECTED", f"TLS packet from {conn.src_ip} to {conn.dst_ip} port {conn.dst_port}")
    #  You can add more logic later using packet_line (size, timing, etc.)
    return False


def send_packet_event_to_server(conn: Connection, spam: bool, packet_info: Optional[dict] = None):
    """
    Sends a small JSON event to your Django server.
    packet_info can hold extra things like packet size, direction, etc.
    """

    headers = {
        "Authorization": f"Bearer {API_JWT_TOKEN}",
        "Content-Type": "application/json",
    }

    data = {
        "hostname": conn.hostname,
        "src_ip": conn.src_ip,
        "src_port": conn.src_port,
        "dst_ip": conn.dst_ip,
        "dst_port": conn.dst_port,
        "is_spam": spam,
        "extra": packet_info or {},
    }

    try:
        resp = requests.post(API_URL, json=data,  timeout=2)
        # Optional: log only on errors
        if resp.status_code >= 400:
            print("[SERVER] Error sending event:", resp.status_code, resp.text)
    except Exception as e:
        print("[SERVER] Exception while sending event:", e)


def analyze_packet_and_report(conn: Connection, packet_line: str):
    """
    This is the function called by packet workers for every packet.
    It:
      1) decides spam / not spam
      2) sends result to server
    """
    spam = is_packet_spam(conn, packet_line)

    # You can parse packet_line for more info; here we keep it simple.
    packet_info = {
        "raw": packet_line,  # or leave this out if you want less data
    }

    send_packet_event_to_server(conn, spam, packet_info)


# ============== FUNCTION 2: PACKET PROCESSORS (PER CONNECTION) ==============

def packet_worker(conn_key: Tuple[Tuple[str, int], Tuple[str, int]]):
    """
    Runs for ONE connection in parallel.
    1) Looks up its Connection object.
    2) Starts tshark with a filter for that connection.
    3) For every packet, calls analyze_packet_and_report().
    4) Stops when the connection is removed from active_connections.
    """

    with state_lock:
        conn = active_connections.get(conn_key)

    if conn is None:
        return  # connection ended before worker even started

    # Build tshark filter for this connection (both directions)
    # We only read incoming packets here (dst is our local machine)
    display_filter = (
        f"(ip.src == {conn.dst_ip} and tcp.srcport == {conn.dst_port} and "
        f"ip.dst == {conn.src_ip} and tcp.dstport == {conn.src_port})"
    )

    tshark_cmd = [
        "tshark",
        "-l",
        "-i", INTERFACE,
        "-Y", display_filter,
        "-T", "fields",
        "-e", "frame.time_relative",
        "-e", "ip.src",
        "-e", "tcp.srcport",
        "-e", "ip.dst",
        "-e", "tcp.dstport",
        "-e", "tcp.len",
    ]

    proc = subprocess.Popen(
        tshark_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )

    print(f"[PKT] Worker started for {conn.hostname} {conn.src_ip}:{conn.src_port} <-> {conn.dst_ip}:{conn.dst_port}")

    try:
        while True:
            # Check if connection is still active
            with state_lock:
                if conn_key not in active_connections:
                    print("[PKT] Connection removed, stopping worker")
                    break

            line = proc.stdout.readline()
            if not line:
                break

            line = line.strip()
            if not line:
                continue

            # Here line has one packet for that connection
            # Example fields: time ip.src srcport ip.dst dstport tcp.len
            # You can parse if you want more info.
            analyze_packet_and_report(conn, line)
    finally:
        proc.terminate()
        print("[PKT] Worker stopped for", conn.hostname)


def packet_manager():
    """
    Continuously watches active_connections.
    For each new connection key that doesn't yet have a packet thread,
    it starts packet_worker in a new thread.
    """
    print("[PKT-MANAGER] Started")
    while True:
        with state_lock:
            # Start a worker thread for each connection without a thread
            for key, conn in list(active_connections.items()):
                if key not in packet_threads:
                    t = threading.Thread(target=packet_worker, args=(key,), daemon=True)
                    packet_threads[key] = t
                    t.start()

            # Clean up threads for connections that no longer exist
            ended_keys = [key for key in packet_threads.keys() if key not in active_connections]
            for key in ended_keys:
                # Thread will exit on its own; we just remove the reference
                packet_threads.pop(key, None)

        # Small sleep to avoid busy loop
        threading.Event().wait(1.0)


# ============== MAIN ==============

def main():
    # 1) Start connection monitor workers
    t_handshake = threading.Thread(target=handshake_worker, daemon=True)
    t_end = threading.Thread(target=end_worker, daemon=True)
    t_handshake.start()
    t_end.start()

    # 2) Start packet manager (which will start per-connection workers)
    t_pkt_manager = threading.Thread(target=packet_manager, daemon=True)
    t_pkt_manager.start()

    print("[MAIN] All workers started. Press Ctrl+C to stop.")

    try:
        while True:
            # You can also print simple stats here if you want
            with state_lock:
                print(f"[MAIN] Active connections: {active_connections}")
            threading.Event().wait(5.0)
    except KeyboardInterrupt:
        print("\n[MAIN] Stopping...")


if __name__ == "__main__":
    main()
