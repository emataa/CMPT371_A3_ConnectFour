# **CMPT 371 A3 Socket Programming `Connect Four`**

**Course:** CMPT 371 - Data Communications & Networking  
**Instructor:** Mirza Zaeem Baig  
**Semester:** Spring 2026  

---

## **Group Members**

| Name | Student ID | Email |
| :---- | :---- | :---- |
| [Kenneth Emata] | [301557091] | [kea31@sfu.ca] |
| [Tommy Truong] | [301304389] | [tttruong@sfu.ca] |

---

## **1. Project Overview & Description**

This project is a multiplayer Connect Four game built using Python's Socket API (TCP). Two clients connect to a central server and play against each other in real time through a graphical tkinter interface. The server handles all game logic such board state management, move validation, and win/draw detection.

---

## **2. System Limitations & Edge Cases**

As required by the project specifications, we have identified and handled (or defined) the following limitations and potential issues within our application scope:

- **Exactly 2 Players Required:**
  - *Solution:* The server accepts exactly 2 clients before starting the game. Each client is handled on its own daemon thread so the main thread stays free.
  - *Limitation:* A third client connecting after the game has started will hang indefinitely — no spectator or queue system is implemented.

- **TCP Stream Buffering:**
  - *Solution:* TCP is a continuous byte stream, meaning multiple JSON messages can arrive concatenated. We append a newline `\n` to every JSON payload and split the receive buffer on `\n` on both sides, so messages are always processed atomically.

- **Thread Safety:**
  - *Solution:* All board mutations on the server are wrapped in a `threading.Lock()` to prevent race conditions if both clients somehow send moves at the same time. On the client, GUI updates are scheduled via `root.after(0, ...)` since tkinter is not thread-safe.

- **No Reconnection Support:**
  - *Limitation:* If either client disconnects mid-game (closes the window, loses network), the session ends for both players. The server does not pause or allow reconnection.

- **Single Game Session:**
  - *Limitation:* The server handles one game at a time. Players can rematch using the in-app **PLAY AGAIN** button, which resets the board without restarting the server.
 
- **Client Disconnection Handling:**
  - *Solution:* If either client disconnects mid-game (closes the window, loses network connection), the connection drop is caught. The remaining player is immediately informed that the server/opponent   disconnected.
  - *Limitation:* The server does not pause or allow players to reconnect to the same match. Instead, the server has to reset to clear the current game state and accept a fresh pair of connections.

- **GUI Requires a Local Display:**
  - *Limitation:* `client.py` uses tkinter and must be run on a machine with a graphical desktop. Running it over a headless SSH session (without X11 forwarding) will crash on startup.

---

## **3. Video Demo**

***RUBRIC NOTE: Include a clickable link.***  
Our 2-minute video demonstration covering connection establishment, data exchange, real-time gameplay, and process termination can be viewed below:  
[**▶️ Watch Project Demo**](#) *(link to be added)*

---

## **4. Prerequisites (Fresh Environment)**

To run this project, you need:

- **Python 3.8** or higher: download from [python.org](https://www.python.org/downloads/) if not installed.
- No external `pip` installations are required (uses standard `socket`, `threading`, `json`, `tkinter` libraries).
- VSCode and/or a terminal

---

## **5. Step-by-Step Run Guide**


### **Step 1: Clone the Repository**

```bash
git clone git@github.com:emataa/CMPT371_A3_ConnectFour.git
cd CMPT371_A3_ConnectFour
```

### **Step 2: Start the Server**

Open a terminal and run:

```bash
python3 server.py
# Console output: "server listening on 8829..."
```

> 💡 **Find your IP address so the other player can connect:**
> - **macOS/Linux:** run `ifconfig` → look for `inet` under your active interface
> - **Windows:** run `ipconfig` → look for `IPv4 Address`
>
> If both players are on the same machine, use `127.0.0.1`.

### **Step 3: Connect Player 1 (Red)**

Open a **new** terminal window. Run the client script:

```bash
python3 client.py
# A "connect four" screen appears. Enter the server IP and click "join game"
# Console output: "player R connected"
```

### **Step 4: Connect Player 2 (Yellow)**

Open a **third** terminal window. Run the client script again:

```bash
python3 client.py
# Enter the same server IP and click "join game"
# Server output: "player Y connected"
# Both clients transition to the game board automatically.
```

### **Step 5: Gameplay**

Standard Connect Four Gameplay

1. **Red** (first to connect) goes first. Click any column to drop your piece.
2. The server updates the board on both screens after every move.
3. **Yellow** takes their turn.
4. The game ends when a player gets four in a row or the board is full.
5. Click **PLAY AGAIN** to reset the board without restarting the server.

---

## **6. Technical Protocol Details (JSON over TCP)**

We designed a custom application-layer protocol for data exchange using JSON over TCP as shown in the TA tutorial:

- **Message Format:** `{"type": <string>, ...}\n`
- **Handshake Phase:**
  - Client sends: `{"type": "CONNECT"}`
  - Server responds: `{"type": "WELCOME", "payload": "R" | "Y"}`
- **Gameplay Phase:**
  - Client sends: `{"type": "MOVE", "col": 0-6}`
  - Server broadcasts: `{"type": "UPDATE", "board": [[...]], "turn": "R"|"Y", "status": "ongoing"|"player R wins!"|"draw", "win_coords": [[r,c], ...]}`
- **Reset Phase:**
  - Client sends: `{"type": "RESET"}`
  - Server broadcasts a fresh `UPDATE` with an empty board and `"status": "ongoing"`

---
 
## **7. Academic Integrity & References**
 
- **Code Origin:**
  - Core game logic and TCP protocol design were written by the group. Game logic is based off Keith Galli's Connect 4 tutorials. Socket boilerplate was adapted from the CMPT 371 course tutorials. 
- **GenAI Usage:**
  - Claude was used to write and format `README.md`.
  - Gemini was used to help with the GUI and Frontend. 
- **References:**
  - [Python Network Programming - TCP/IP Socket Programming](https://www.youtube.com/playlist?list=PLhTjy8cBISErYuLZUvVOYsR1giva2payF)
  - [CMPT 371 Assignment 3: TA Guided Tutorial](https://docs.python.org](https://www.youtube.com/playlist?list=PL-8C2cUhmkO1yWLTCiqf4mFXId73phvdx)/3/library/threading.html)
  - [Keith Galli: How to Program Connect 4 in Python](https://www.youtube.com/watch?v=UYgyRArKDEs&list=PLFCB5Dp81iNV_inzM-R9AKkZZlePCZdtV)
