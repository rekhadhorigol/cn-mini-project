# CN Mini Project - Real Time Multiplayer Game Networking Engine

This project is a simple multiplayer game system built using UDP communication. The main idea is to simulate how multiple games can run at the same time without waiting for each other.

The system has four main parts:
1. Frontend (browser interface)
2. Bridge (connects web to UDP server)
3. Server (handles game logic and communication)
4. Client (to show stats like latency, jitter, packet loss etc.)

Messages between the bridge and server are encrypted for security. Multiple clients can connect and play different games simultaneously.

The server also stores game activity in a database for tracking purposes.

## Technologies used:
- Python (socket programming, threading)
- Flask + Socket.IO (for frontend connection)
- SQLite (database)
- HTML (Structure of web interface)
- CSS (Styling)
- JavaScript (Frontend logic & Socket.IO client)
- AES Encryption (Secure transmission of game data)
- UDP Protocol (Low-latency communication for real-time gameplay)

## Steps:
1) Clone the repo & open it in vs code.
2) Open terminal 1:
```bash
python server.py
```
3) Open terminal 2:
```bash
cd CN_Game_Web
python bridge.py
```
(follow the link displayed in the terminal to open & use the website)

4) Open terminal 3: (optional to simulate ping & see stats)
```bash
python client.py
```
If you have sql extension, then you can also view the db named **game_data.db** once you start the server.

This project demonstrates basic networking concepts like UDP communication, parallel processing and secure data transmission.
