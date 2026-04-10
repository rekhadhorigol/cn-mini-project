"""
client.py — UDP Network Demo Client
=====================================
Demonstrates: AES-128 encrypted UDP, latency, jitter, packet loss

Commands:
  /ping      — single latency measurement
  /autoping  — continuous ping every 2s (toggle)
  /stats     — latency, jitter, packet loss, sent, received, samples
  /quit      — exit
"""

import socket
import threading
import time
from crypto_config import aes_encrypt, aes_decrypt

SERVER_IP   = "127.0.0.1"
PORT        = 5000
BUFFER_SIZE = 4096

client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client.bind(("0.0.0.0", 0))      # let OS assign local port (fixes WinError 10022)
client.settimeout(5.0)

# ─── STATS ──────────────────────────────────────────────────
lock             = threading.Lock()
sent_packets     = 0
received_packets = 0
seq_number       = 0
latency_samples  = []    # rolling window of last 20 pings
last_ping_time   = None
autoping_active  = False

def record_latency(ms):
    with lock:
        latency_samples.append(ms)
        if len(latency_samples) > 20:
            latency_samples.pop(0)

def get_stats():
    with lock:
        samples = latency_samples[:]
        tx = sent_packets
        rx = received_packets
    if not samples:
        return None
    avg    = sum(samples) / len(samples)
    jitter = sum(abs(samples[i] - samples[i-1])
                 for i in range(1, len(samples))) / max(1, len(samples) - 1)
    loss   = round(100 * max(0, tx - rx) / max(1, tx), 1)
    return {
        "avg":     round(avg, 2),
        "min":     round(min(samples), 2),
        "max":     round(max(samples), 2),
        "jitter":  round(jitter, 2),
        "loss":    loss,
        "sent":    tx,
        "recv":    rx,
        "samples": len(samples),
    }

def send_ping():
    global sent_packets, seq_number, last_ping_time
    with lock:
        seq_number   += 1
        seq           = seq_number
        sent_packets += 1
        last_ping_time = time.time()
    client.sendto(aes_encrypt(f"SEQ:{seq}|PING"), (SERVER_IP, PORT))

# ─── RECEIVE THREAD ─────────────────────────────────────────
def receive():
    global received_packets, last_ping_time
    while True:
        try:
            data, _ = client.recvfrom(BUFFER_SIZE)
            message  = aes_decrypt(data)
            with lock:
                received_packets += 1

            if message == "PONG":
                with lock:
                    t0 = last_ping_time
                    last_ping_time = None
                if t0:
                    ms = (time.time() - t0) * 1000
                    record_latency(ms)
                    s = get_stats()
                    print(f"\n  [PONG]  Latency: {ms:.2f} ms"
                          f"   Jitter: {s['jitter']:.2f} ms"
                          f"   Loss: {s['loss']}%")

        except socket.timeout:
            continue
        except Exception as e:
            print(f"  [error] {e}")
            time.sleep(0.5)

threading.Thread(target=receive, daemon=True).start()

# ─── AUTOPING ───────────────────────────────────────────────
def autoping_loop():
    global autoping_active
    print("  [AutoPing] Running — /autoping again to stop\n")
    while autoping_active:
        send_ping()
        time.sleep(2)
    print("  [AutoPing] Stopped\n")

# ─── STARTUP ────────────────────────────────────────────────
W = 42
print("UDP CLIENT  -  AES-128 Encrypted")
print("CN Mini Project Demo")
print()
print("  Commands:")
print("    /ping      — measure latency & jitter")
print("    /autoping  — continuous ping (toggle)")
print("    /stats     — full network stats")
print("    /quit      — exit")
print()

# ─── MAIN LOOP ──────────────────────────────────────────────
while True:
    try:
        msg = input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  Goodbye.")
        break

    if not msg:
        continue

    if msg == "/ping":
        print("  Sending PING...")
        send_ping()
        continue

    if msg == "/autoping":
        autoping_active = not autoping_active
        if autoping_active:
            threading.Thread(target=autoping_loop, daemon=True).start()
        else:
            print("  [AutoPing] Stopping...")
        continue

    if msg == "/stats":
        s = get_stats()
        div = "├" + "─" * W + "┤"
        def row(label, value):
            print("│" + f"  {label:<14} {value}".ljust(W) + "│")
        print()
        print("┌" + "─" * W + "┐")
        print("│" + "  NETWORK STATISTICS".center(W) + "│")
        print(div)
        if s:
            row("Avg Latency :", f"{s['avg']:.2f} ms")
            row("Min Latency :", f"{s['min']:.2f} ms")
            row("Max Latency :", f"{s['max']:.2f} ms")
            row("Jitter      :", f"{s['jitter']:.2f} ms")
            row("Packet Loss :", f"{s['loss']} %")
            row("Sent        :", str(s['sent']))
            row("Received    :", str(s['recv']))
            row("Samples     :", str(s['samples']))
        else:
            print("│" + "  No data yet — run /ping first".ljust(W) + "│")
        print("└" + "─" * W + "┘")
        print()
        continue

    if msg == "/quit":
        print("  Goodbye.")
        break

    print("  Unknown command. Try /ping  /autoping  /stats  /quit")
