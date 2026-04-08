"""
CMPT 371 A3: Connect Four 
server.py - connect four server
-----------------------------------------
INBOUND (Client -> Server):
  - Handshake: {"type": "CONNECT"}
  - Gameplay:  {"type": "MOVE", "col": 0-6}

OUTBOUND (Server -> Client):
  - Assign:    {"type": "WELCOME", "role": "R" | "Y"}
  - State:     {"type": "UPDATE", "board": [[...]], "turn": "R", "status": "..."}

Technical: UTF-8 JSON + Newline (\n) Delimiter
  - "\n" marks where one JSON object ends so the receiver can split and parse them.

"""

import socket, json, threading, os

PORT = 5050
ROWS, COLS = 6, 7

class ConnectFourServer:
    def __init__(self):
        self.board = [["0"] * COLS for _ in range(ROWS)]  # 6x7 grid, "0" = empty
        self.clients = []        # list of (socket, role) for each connected player
        self.turn = "R"          # Red always goes first
        self.game_over = False
        self.lock = threading.Lock()  # prevents race conditions when two clients send moves at the same time

    def start(self):
        # create the TCP server socket and wait for exactly 2 players
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # allows reuse of port immediately after restart
        s.bind(("0.0.0.0", PORT))
        s.listen(2)
        print(f"server listening on {PORT}...")

        while len(self.clients) < 2:
            conn, addr = s.accept()
            role = "R" if not self.clients else "Y"  # first to connect is Red, second is Yellow
            self.clients.append((conn, role))
            print(f"player {role} connected")
            
            # start a listener thread for each client immediately so CONNECT handshake isn't missed
            threading.Thread(target=self.handle_client, args=(conn, role), daemon=True).start()

        # both players connected, send the initial board state to kick off the game
        self.broadcast("ongoing")
        
        while True: threading.Event().wait(1)

    def broadcast(self, status, win_coords=None):
        # send the full game state to every connected client
        msg = {"type": "UPDATE", "board": self.board, "turn": self.turn, "status": status, "win_coords": win_coords}
        data = (json.dumps(msg) + "\n").encode()
        for conn, role in self.clients:
            try: conn.sendall(data)
            except: pass  

      
    def handle_client(self, conn, role):
        #runs on its own thread
        buf = ""
        try:
            while True:
                raw = conn.recv(4096).decode()
                if not raw: break # connection closed
                
                #split on \n
                buf += raw
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    msg = json.loads(line)
                    
                    if msg["type"] == "CONNECT":
                        # Handshake response
                        resp = json.dumps({"type": "WELCOME", "payload": role}) + "\n"
                        conn.sendall(resp.encode())
                    
                    elif msg["type"] == "MOVE":
                        self.do_move(role, msg["col"])
                        
                    elif msg["type"] == "RESET":
                        with self.lock:
                            self.board = [["0"] * COLS for _ in range(ROWS)]
                            self.turn, self.game_over = "R", False
                            self.broadcast("ongoing")
        
        # if we exit the loop, the client has disconnected
        except:
            print(f"error handling player {role}")
        finally:
            print(f"player {role} disconnected. shutting down.")
            conn.close()
            os._exit(0)

        

    def do_move(self, role, col):
        with self.lock:
            # ignore move if game is over or it's not this player's turn
            if self.game_over or role != self.turn: return
            
            # find the lowest empty row in the chosen column 
            row = -1
            for r in range(ROWS-1, -1, -1):
                if self.board[r][col] == "0":
                    row = r
                    break
            
            if row == -1: return  # column is full, ignore move
            
            self.board[row][col] = role
            win_line = self.check_win(row, col, role)
            
            if win_line:
                self.game_over = True
                self.broadcast(f"player {role} wins!", win_line)
            elif all(self.board[0][c] != "0" for c in range(COLS)):
                # top row is full = board is full = draw
                self.game_over = True
                self.broadcast("draw")
            else:
                self.turn = "Y" if role == "R" else "R"  # switch turns
                self.broadcast("ongoing")

    def check_win(self, r, c, color):
        # check all 4 directions: horizontal, vertical, diagonal, anti-diagonal
        for dr, dc in [(0,1), (1,0), (1,1), (1,-1)]:
            line = [(r, c)]
            for side in [1, -1]:
                # extend in both directions along the axis
                nr, nc = r + dr*side, c + dc*side
                while 0 <= nr < ROWS and 0 <= nc < COLS and self.board[nr][nc] == color:
                    line.append((nr, nc))
                    nr, nc = nr + dr*side, nc + dc*side
            if len(line) >= 4: return line[:4]  # return the winning 4 cells for highlighting
        return None

if __name__ == "__main__":
    ConnectFourServer().start()