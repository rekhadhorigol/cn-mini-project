"""
server.py - UDP Game Server
============================
Security  : AES-128-CBC + HMAC-SHA256 via Fernet
Parallel  : ThreadPoolExecutor - each packet in its own worker thread
Tick Rate : 10 ticks/sec background loop
"""

import socket
import sqlite3
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from crypto_config import aes_encrypt, aes_decrypt

SERVER_IP   = "0.0.0.0"
PORT        = 5000
BUFFER_SIZE = 4096
TICK_RATE   = 10
TICK_DELAY  = 1 / TICK_RATE
MAX_WORKERS = 20

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind((SERVER_IP, PORT))

print(f"Server running on {SERVER_IP}:{PORT}")
print(f"AES-128 (Fernet) encryption active")
print(f"Thread pool: {MAX_WORKERS} workers  |  Tick rate: {TICK_RATE} Hz\n")

# --- DATABASE ---------------------------------------------------
db_lock = threading.Lock()
conn    = sqlite3.connect("game_data.db", check_same_thread=False)
cursor  = conn.cursor()

cursor.executescript("""
CREATE TABLE IF NOT EXISTS game_log(
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    game_type TEXT,
    game_id   TEXT,
    player    TEXT,
    action    TEXT,
    detail    TEXT,
    timestamp TEXT
);
""")
conn.commit()
print("DB ready: game_log\n")

# --- MOVEMENT CLIENT REGISTRY -----------------------------------
# Used for broadcasting movement game messages to CLI clients.
# This is UDP address discovery - not a TCP connection.
# The server learns a client's address from the first packet they send.
clients_lock = threading.Lock()
clients      = {}   # addr -> player_name

def broadcast(message: str, exclude_addr=None):
    data = aes_encrypt(message)
    with clients_lock:
        targets = list(clients.keys())
    for addr in targets:
        if addr != exclude_addr:
            try:
                server.sendto(data, addr)
            except Exception as e:
                print(f"Broadcast to {addr} failed: {e}")

# --- DB HELPER --------------------------------------------------
IST_OFFSET = 5.5 * 3600   # UTC+5:30 in seconds

def ist_now():
    """Return current IST time as a formatted string."""
    ist = time.gmtime(time.time() + IST_OFFSET)
    return time.strftime("%Y-%m-%d %H:%M:%S IST", ist)

def db_insert(game_type, game_id, player, action, detail=""):
    with db_lock:
        try:
            cursor.execute(
                "INSERT INTO game_log(game_type,game_id,player,action,detail,timestamp) VALUES(?,?,?,?,?,?)",
                (game_type, game_id, player, action, detail, ist_now())
            )
            conn.commit()
            print(f"DB <- [{game_type}] {game_id} | {player} | {action} | {detail}")
        except Exception as e:
            print(f"DB error: {e}")

# --- TICK LOOP --------------------------------------------------
tick_count = 0

def tick_loop():
    global tick_count
    while True:
        time.sleep(TICK_DELAY)
        tick_count += 1

threading.Thread(target=tick_loop, daemon=True).start()

# --- PACKET HANDLER (runs in thread pool) -----------------------
def handle_packet(data: bytes, addr: tuple):
    try:
        message = aes_decrypt(data)
    except Exception:
        print(f"Decrypt failed from {addr} - wrong key or tampered packet")
        return

    # Strip sequence number prefix if present
    if message.startswith("SEQ:"):
        try:
            _, message = message.split("|", 1)
        except Exception:
            pass

    print(f"Received from {addr}: {message}")

    parts     = message.split("|")
    game_type = parts[0] if parts else ""

    # PING / PONG - latency measurement
    if game_type == "PING":
        try:
            server.sendto(aes_encrypt("PONG"), addr)
        except Exception as e:
            print(f"PONG failed: {e}")
        return

    # CLICK GAME
    # click|<game_id>|<player>|click|<score>
    # click|<game_id>|<player>|win|<score>
    if game_type == "click" and len(parts) == 5:
        _, game_id, player, action, detail = parts
        db_insert("click", game_id, player, action, detail)
        return

    # GUESS GAME
    # guess|<game_id>|<player>|guess|<number>
    # guess|<game_id>|<player>|correct|<number>
    if game_type == "guess" and len(parts) == 5:
        _, game_id, player, action, detail = parts
        db_insert("guess", game_id, player, action, detail)
        return

    # XOX GAME
    # xox|<game_id>|<player>|move|<symbol>:<position>
    # xox|<game_id>|<player>|result|win/lose/draw
    if game_type == "xox" and len(parts) == 5:
        _, game_id, player, action, detail = parts
        db_insert("xox", game_id, player, action, detail)
        return

    # MOVEMENT / CHAT
    # move|<game_id>|<player>|move|<direction>
    # move|<game_id>|<player>|shoot|
    # move|<game_id>|<player>|chat|<text>
    # move|<game_id>|<player>|join|
    if game_type == "move" and len(parts) >= 4:
        _, game_id, player, action = parts[:4]
        detail = "|".join(parts[4:])
        db_insert("move", game_id, player, action, detail)
        if action in ("move", "shoot", "chat", "join"):
            broadcast(message, exclude_addr=addr)
        return

    # JOIN - UDP address discovery for movement game broadcasts
    if "joined the game" in message:
        player_name = message.replace(" joined the game", "").strip()
        with clients_lock:
            clients[addr] = player_name
        print(f"Discovered: {player_name} at {addr}")
        broadcast(message, exclude_addr=addr)
        return

    # Fallback - broadcast anything unrecognised
    broadcast(message, exclude_addr=addr)

# --- MAIN RECEIVE LOOP ------------------------------------------
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
print("Listening - packets dispatched to thread pool\n")

while True:
    try:
        data, addr = server.recvfrom(BUFFER_SIZE)
        executor.submit(handle_packet, data, addr)
    except Exception as e:
        print(f"Receive error: {e}")
