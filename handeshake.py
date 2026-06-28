import subprocess
import threading
import queue

def http_host_worker():
    interfaces = ["5", "6"]  # same as your PowerShell command
    q = queue.Queue()

    base_cmd = [
        "tshark",
        "-l",
        "-n",
        "-Y", "tls.handshake.type == 1 || http.request",
        "-T", "fields",
        "-e", "ip.src",
        "-e", "tcp.srcport",
        "-e", "ip.dst",
        "-e", "tcp.dstport",
        "-e", "tls.handshake.extensions_server_name",
        "-e", "http.host",
    ]

    procs = []

    def reader(proc, iface):
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                line = line.strip()
                if line:
                    q.put((iface, line))
        except Exception:
            pass

    for iface in interfaces:
        cmd = base_cmd.copy()
        cmd.insert(2, iface)
        cmd.insert(2, "-i")

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,   # DO NOT HIDE ERRORS
            text=True,
            bufsize=1,
        )
        procs.append((iface, proc))
        threading.Thread(target=reader, args=(proc, iface), daemon=True).start()
        print(f"[HTTP] Listening on interface {iface}")

    try:
        while True:
            # iface, host = q.get()
            print(f"[HTTP][iface] host={q.get()} ")
    finally:
        for _, p in procs:
            try:
                p.terminate()
            except Exception:
                pass

if __name__ == "__main__":
    http_host_worker()