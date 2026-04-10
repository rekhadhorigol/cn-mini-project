"""
bridge.py - Flask + Socket.IO Web Bridge
==========================================
Serves the HTML game website and forwards all game events
to server.py via AES-encrypted UDP packets.
"""

from flask import Flask, render_template
from flask_socketio import SocketIO
import random
import socket
import sys
import os
import uuid

# Add parent dir so crypto_config is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from crypto_config import aes_encrypt

app      = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- UDP -> server.py -------------------------------------------
UDP_IP   = "127.0.0.1"
UDP_PORT = 5000
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def udp(message: str):
    """AES-encrypt and forward to server.py over UDP."""
    try:
        udp_sock.sendto(aes_encrypt(message), (UDP_IP, UDP_PORT))
        print(f"UDP -> {message}")
    except Exception as e:
        print(f"UDP send failed: {e}")

# --- ROUTE ------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# --- CLICK RACE -------------------------------------------------
# UDP format:
#   click|<game_id>|<player>|click|<score>
#   click|<game_id>|<player>|win|<score>
click_game_id = uuid.uuid4().hex[:8]
click_scores  = {}

@socketio.on("click_update")
def click_update(data):
    global click_game_id, click_scores
    player = data["name"]
    score  = int(data["score"])
    click_scores[player] = score

    udp(f"click|{click_game_id}|{player}|click|{score}")
    socketio.emit("click_update", click_scores)

    if score >= 20:
        udp(f"click|{click_game_id}|{player}|win|{score}")
        click_scores  = {}
        click_game_id = uuid.uuid4().hex[:8]


# --- GUESS GAME -------------------------------------------------
# UDP format:
#   guess|<game_id>|<player>|guess|<number>
#   guess|<game_id>|<player>|correct|<number>
secret_number = random.randint(1, 10)
guess_game_id = uuid.uuid4().hex[:8]

@socketio.on("guess")
def handle_guess(data):
    global secret_number, guess_game_id
    player = data["name"]
    guess  = int(data["guess"])

    udp(f"guess|{guess_game_id}|{player}|guess|{guess}")

    if guess == secret_number:
        udp(f"guess|{guess_game_id}|{player}|correct|{guess}")
        socketio.emit("guess_result", f"{player} guessed correctly! It was {secret_number}")
        secret_number = random.randint(1, 10)
        guess_game_id = uuid.uuid4().hex[:8]
    elif guess < secret_number:
        socketio.emit("guess_result", f"{player}: Too low (guessed {guess})")
    else:
        socketio.emit("guess_result", f"{player}: Too high (guessed {guess})")


# --- XOX GAME ---------------------------------------------------
# UDP format:
#   xox|<game_id>|<player>|move|<symbol>:<position>
#   xox|<game_id>|<player>|result|win/lose/draw
class XOXState:
    def __init__(self):
        self.board   = [""] * 9
        self.turn    = "X"
        self.players = {}
        self.game_id = uuid.uuid4().hex[:8]

xox = XOXState()

def check_winner(board):
    for a, b, c in [[0,1,2],[3,4,5],[6,7,8],
                    [0,3,6],[1,4,7],[2,5,8],
                    [0,4,8],[2,4,6]]:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a], [a, b, c]
    if "" not in board:
        return "draw", None
    return None, None

@socketio.on("xox_move_simple")
def xox_move(data):
    index  = int(data["index"])
    player = data["player"]

    if xox.board[index] != "":
        return
    if player not in xox.players:
        if "X" not in xox.players.values():
            xox.players[player] = "X"
        elif "O" not in xox.players.values():
            xox.players[player] = "O"
        else:
            return
    symbol = xox.players[player]
    if symbol != xox.turn:
        return

    xox.board[index] = symbol
    udp(f"xox|{xox.game_id}|{player}|move|{symbol}:{index}")

    result, winLine = check_winner(xox.board)
    winnerName = None
    if result and result != "draw":
        winnerName = next((p for p, s in xox.players.items() if s == result), None)

    if not result:
        xox.turn = "O" if xox.turn == "X" else "X"

    socketio.emit("xox_update_simple", {
        "board": xox.board, "turn": xox.turn,
        "result": result, "winnerName": winnerName, "winLine": winLine
    })

    if result:
        for p in xox.players:
            outcome = "draw" if result == "draw" else ("win" if p == winnerName else "lose")
            udp(f"xox|{xox.game_id}|{p}|result|{outcome}")
        xox.board   = [""] * 9
        xox.turn    = "X"
        xox.players = {}
        xox.game_id = uuid.uuid4().hex[:8]

@socketio.on("xox_reset")
def xox_reset_handler():
    xox.board   = [""] * 9
    xox.turn    = "X"
    xox.players = {}
    xox.game_id = uuid.uuid4().hex[:8]
    socketio.emit("xox_update_simple", {
        "board": xox.board, "turn": xox.turn,
        "result": None, "winnerName": None, "winLine": None
    })


# --- MOVEMENT GAME ----------------------------------------------
# UDP format:
#   move|<game_id>|<player>|join|
#   move|<game_id>|<player>|move|<direction>
#   move|<game_id>|<player>|shoot|
#   move|<game_id>|<player>|chat|<text>
move_game_id = uuid.uuid4().hex[:8]

@socketio.on("send_message")
def handle_message(data):
    message = data.get("message", "")
    player  = data.get("player", "unknown")

    if message.endswith(" joined the game"):
        udp(f"move|{move_game_id}|{player}|join|")
    elif " moved " in message:
        direction = message.split(" moved ")[-1].strip()
        udp(f"move|{move_game_id}|{player}|move|{direction}")
    elif message.endswith(" shot"):
        udp(f"move|{move_game_id}|{player}|shoot|")
    else:
        text = message.split(": ", 1)[1] if ": " in message else message
        udp(f"move|{move_game_id}|{player}|chat|{text}")

    socketio.emit("receive_message", data)


# --- RUN --------------------------------------------------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8000)
