CN Mini Project – Multiplayer Game System

This project is a simple multiplayer game system built using UDP communication. The main idea is to simulate how multiple games can run at the same time without waiting for each other.

The system has three main parts:
1. Frontend (browser interface)
2. Bridge (connects web to UDP server)
3. Server (handles game logic and communication)

Messages between the bridge and server are encrypted for security. Multiple clients can connect and play different games simultaneously.

The server also stores game activity in a database for tracking purposes.

Technologies used:
- Python (socket programming, threading)
- Flask + Socket.IO (for frontend connection)
- SQLite (database)

This project demonstrates basic networking concepts like UDP communication, parallel processing, and secure data transmission.