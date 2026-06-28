from asyncio import threads
import subprocess
import threading
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
import tkinter as tk
from tkinter import messagebox
import webbrowser
import requests  

# ===================== CONFIG ====================

API_LOGIN_URL = "http://127.0.0.1:8000/api/login/"       # Django login API
SIGNUP_PAGE_URL = "http://localhost:5173/auth/signup"     # Signup webpage

# Interface name
INTERFACE = "Wi-Fi"   # change to your actual interface name


MONITORED_HOSTS = {
    # Meta / Facebook
    "facebook.com",
    "fbcdn.net",
    "gateway.facebook.com",
    "edge-mqtt.facebook.com",

    # Instagram / Threads (Meta)
    "instagram.com",
    "cdninstagram.com",
    "threads.net",
    "www.instagram.com",
    "instagram.com",
    "i.instagram.com",
    "graph.instagram.com",
    "static.cdninstagram.com",
    "cdninstagram.com",
    "threads.net",

    # X / Twitter
    "x.com",
    "twitter.com",
    "twimg.com",
    "x.com",
    "twitter.com",
    "api.twitter.com",
    "t.co",
    "pbs.twimg.com",
    "video.twimg.com",
    "twimg.com",
    # LinkedIn
    "linkedin.com",
    "www.linkedin.com",
    "linkedin.com",
    "static.licdn.com",
    "licdn.com",
    "platform.linkedin.com",
    "merchantpool1.linkedin.com",
    "pk.linkedin.com",
    "static.licdn.com",
    }


# Django server endpoint
API_URL = "http://localhost:8000/api/packets/"   # change to your real endpoint

# Will be set after login automatically
API_JWT_TOKEN = ""


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

active_connections: Dict[Tuple[Tuple[str, int], Tuple[str, int]], Connection] = {}
packet_threads: Dict[Tuple[Tuple[str, int], Tuple[str, int]], threading.Thread] = {}
state_lock = threading.Lock()


# ============== FUNCTION 1: CONNECTION MONITOR ==============



import queue

def handshake_worker():
    """
    Captures both:
      - TLS ClientHello SNI (tls.handshake.type == 1)
      - HTTP requests (http.request)
    from interfaces 5 and 6 concurrently, then inserts connections into active_connections.
    """

    interfaces = ["4", "5"]  # change to ["5","7"] if those are your real ones
    q: "queue.Queue[tuple[str, str]]" = queue.Queue(maxsize=5000)

    # IMPORTANT: use -E separator so parsing is reliable even if fields are empty
    base_cmd = [
        "tshark",
        "-l",
        "-n",
        "-Y", "(tls.handshake.type == 1) || (http.request)",
        "-T", "fields",
        "-E", "separator=\t",
        "-E", "occurrence=f",
        "-e", "ip.src",
        "-e", "tcp.srcport",
        "-e", "ip.dst",
        "-e", "tcp.dstport",
        "-e", "tls.handshake.extensions_server_name",
        "-e", "http.host",
    ]

    procs = []

    def reader(proc: subprocess.Popen, iface: str):
        """Read tshark output and push lines into queue without blocking other interfaces."""
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    q.put_nowait((iface, line))
                except queue.Full:
                    # Drop one old line to avoid deadlock if overloaded
                    try:
                        q.get_nowait()
                        q.put_nowait((iface, line))
                    except Exception:
                        pass
        except Exception:
            pass

    # Start one tshark process per interface
    for iface in interfaces:
        cmd = base_cmd.copy()
        cmd.insert(2, iface)
        cmd.insert(2, "-i")

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,   # keep errors visible
            text=True,
            bufsize=1,
        )
        procs.append((iface, proc))
        threading.Thread(target=reader, args=(proc, iface), daemon=True).start()
        # print(f"[CAPTURE] Listening on interface {iface}")

    try:
        while True:
            iface, line = q.get()  # blocks until a line arrives

            # Because we used tab separator, we can reliably split into 6 fields
            parts = line.split("\t")
            # Expecting: ip.src, tcp.srcport, ip.dst, tcp.dstport, sni, http.host
            if len(parts) < 4:
                continue

            src_ip = parts[0].strip()
            src_port_str = parts[1].strip()
            dst_ip = parts[2].strip()
            dst_port_str = parts[3].strip()
            sni = parts[4].strip() if len(parts) >= 5 else ""
            http_host = parts[5].strip() if len(parts) >= 6 else ""

            # Pick hostname: prefer SNI, else HTTP host
            hostname = sni or http_host
            if not hostname:
                continue

            # Optional: normalize host (tshark sometimes returns multiple hosts or includes commas)
            hostname = hostname.split(",")[0].strip()
            # print(hostname)
            # Apply your monitored host filter (optional)
            if hostname=="127.0.0.1:3000":
                messagebox.showwarning("spam detected m2", f"TLS packets from{src_ip} to {dst_ip} port{dst_port_str} ")
                continue
            if hostname not in MONITORED_HOSTS:
                continue
            try:
                src_port = int(src_port_str)
                dst_port = int(dst_port_str)
            except ValueError:
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
                    # print(f"[NEW][iface {iface}] {src_ip}:{src_port} -> {dst_ip}:{dst_port} host={hostname}")

    finally:
        for _, p in procs:
            try:
                p.terminate()
            except Exception:
                pass
        # print("[CAPTURE] Worker stopped")



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

    # print("[END] Listening for TCP FIN/RST on", INTERFACE)

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

            # IMPORTANT: normalized key (same as Connection.key())
            key = make_key(src_ip, src_port, dst_ip, dst_port)

            with state_lock:
                removed_conn = active_connections.pop(key, None)
                # if removed_conn is not None:
                    # print(f"[END] {src_ip}:{src_port} <-> {dst_ip}:{dst_port} host={removed_conn.hostname}")
    finally:
        proc.terminate()
        # print("[END] Worker stopped")


# ============== FUNCTION 3: SPAM DETECTION + SEND TO SERVER ==============

def is_packet_spam(conn: Connection, packet_line: str) -> bool:
    """
    Signature-based malicious packet detection
    """
    if conn.hostname not in MONITORED_HOSTS and conn.dst_port == 443:
        messagebox.showwarning("spam detected", f"TLS 2 packets from{conn.src_ip} to {conn.dst_ip} port{conn.dst_port} ")
        return True

    return False
def send_packet_event_to_server(conn: Connection, spam: bool, packet_info: Optional[dict] = None):
    """
    Sends a small JSON event to your Django server.
    Uses API_JWT_TOKEN set after login.
    """
    global API_JWT_TOKEN

    if not API_JWT_TOKEN:
        # print("[SERVER] No JWT token set. Skipping send.")
        return

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
        # print(API_JWT_TOKEN)
        resp = requests.post(API_URL, headers=headers, json=data, timeout=2)
        if resp.status_code >= 400:
            pass
            # print("[SERVER] Error sending event:", resp.status_code, resp.text)
    except Exception as e:
        pass
        # print("[SERVER] Exception while sending event:", e)


def analyze_packet_and_report(conn: Connection, packet_line: str):
    spam = is_packet_spam(conn, packet_line)
    packet_info = {"raw": packet_line}
    send_packet_event_to_server(conn, spam, packet_info)


# ============== FUNCTION 2: PACKET PROCESSORS (PER CONNECTION) ==============

def packet_worker(conn_key: Tuple[Tuple[str, int], Tuple[str, int]]):
    with state_lock:
        conn = active_connections.get(conn_key)

    if conn is None:
        return

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

    # print(f"[PKT] Worker started for {conn.hostname} {conn.src_ip}:{conn.src_port} <-> {conn.dst_ip}:{conn.dst_port}")

    try:
        while True:
            with state_lock:
                if conn_key not in active_connections:
                    # print("[PKT] Connection removed, stopping worker")
                    break

            line = proc.stdout.readline()
            if not line:
                break

            line = line.strip()
            if not line:
                continue

            analyze_packet_and_report(conn, line)
    finally:
        proc.terminate()
        # print("[PKT] Worker stopped for", conn.hostname)


def packet_manager():
    print("[PKT-MANAGER] Started")
    while True:
        with state_lock:
            for key in list(active_connections.keys()):
                if key not in packet_threads:
                    t = threading.Thread(target=packet_worker, args=(key,), daemon=True)
                    packet_threads[key] = t
                    t.start()

            ended_keys = [key for key in packet_threads.keys() if key not in active_connections]
            for key in ended_keys:
                packet_threads.pop(key, None)

        threading.Event().wait(1.0)


# ===================== LOGIN GUI =====================

class LoginApp:
    def __init__(self, root):
        self.root = root
        root.title("Login")
        root.geometry("350x260")
        root.resizable(False, False)

        tk.Label(root, text="Welcome", font=("Arial", 18, "bold")).pack(pady=10)

        tk.Label(root, text="Username").pack()
        self.username_entry = tk.Entry(root, width=30)
        self.username_entry.pack(pady=5)

        tk.Label(root, text="Password").pack()
        self.password_entry = tk.Entry(root, show="*", width=30)
        self.password_entry.pack(pady=5)

        tk.Button(root, text="Login", width=15, command=self.login).pack(pady=15)
        tk.Button(root, text="Create New Account", width=20, command=self.open_signup).pack()

    def open_signup(self):
        webbrowser.open(SIGNUP_PAGE_URL)

    def login(self):
        global API_JWT_TOKEN

        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            messagebox.showerror("Error", "Please enter username and password")
            return

        try:
            payload = {"username": username, "password": password}
            response = requests.post(API_LOGIN_URL, json=payload, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # Your old code suggests: token is a dict -> token['access']
                token_obj = data.get("token")
                if not token_obj:
                    messagebox.showerror("Error", "No token returned by server")
                    return

                # Support both cases: token string OR {"access": "...", "refresh": "..."}
                if isinstance(token_obj, dict) and "access" in token_obj:
                    API_JWT_TOKEN = token_obj["access"]
                else:
                    API_JWT_TOKEN = str(token_obj)

                messagebox.showinfo("Success", "Login Successful!")
                self.root.destroy()
                start_monitoring_system()

            else:
                try:
                    msg = response.json().get("detail", "Invalid credentials")
                except Exception:
                    msg = "Invalid login"
                messagebox.showerror("Login Failed", msg)

        except requests.exceptions.RequestException as e:
            messagebox.showerror("Network Error", f"Could not reach server\n{e}")


# ===================== START MONITORING =====================

def start_monitoring_system():
    t_handshake = threading.Thread(target=handshake_worker, daemon=True)
    t_end = threading.Thread(target=end_worker, daemon=True)
    t_pkt_manager = threading.Thread(target=packet_manager, daemon=True)

    t_handshake.start()
    t_end.start()
    t_pkt_manager.start()

    # print("[MAIN] All workers started. Press Ctrl+C to stop.")

    try:
        while True:
            with state_lock:
                pass
                # print(f"[MAIN] Active connections count: {len(active_connections)}")
            threading.Event().wait(5.0)
    except KeyboardInterrupt:
        print("\n[MAIN] Stopping...")


# ===================== RUN APP =====================

if __name__ == "__main__":
    root = tk.Tk()
    app = LoginApp(root)
    root.mainloop()
