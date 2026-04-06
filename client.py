"""
CMPT 371 A3: Connect Four 
client.py - connect four client
-----------------------------------------
OUTBOUND (Client -> Server):
  - Handshake: {"type": "CONNECT"}
  - Gameplay:  {"type": "MOVE", "col": 0-6}

INBOUND (Server -> Client):
  - Assign:    {"type": "WELCOME", "role": "R" | "Y"}
  - State:     {"type": "UPDATE", "board": [[...]], "turn": "R", "status": "..."}

Technical: UTF-8 JSON + Newline (\n) Delimiter
  - "\n" marks where one JSON object ends so the receiver can split and parse them.

"""

import socket, json, threading
import tkinter as tk

PORT = 5050
ROWS, COLS = 6, 7

THEME = {
    "bg": "#0f172a", "card": "#1e293b", "accent": "#38bdf8",
    "red": "#ef4444", "yel": "#f59e0b", "hole": "#334155",
    "cell": 80, "space": 10, "face": "courier"
}

class ConnectFourClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Connect Four")
        self.root.geometry("700x850")
        self.root.configure(bg=THEME["bg"])
        
        # game state 
        # updated by the network thread, read by the GUI
        self.board = [["0"] * COLS for _ in range(ROWS)]
        self.role, self.game_over, self.sock, self.win_line = None, False, None, []

        self.main = tk.Frame(self.root, bg=THEME["bg"])
        self.main.place(relx=0.5, rely=0.5, anchor="center")
        
        self.show_login()

    def show_login(self):
        # simple landing screen with IP input and a connect button
        self.login = tk.Frame(self.main, bg=THEME["bg"])
        self.login.pack()
        
        tk.Label(self.login, text="connect four", font=(THEME["face"], 32, "bold"), fg=THEME["accent"], bg=THEME["bg"]).pack(pady=20)
        self.ip_in = tk.Entry(self.login, font=(THEME["face"], 14), bg=THEME["card"], fg="white", justify="center", relief="flat")
        self.ip_in.insert(0, "127.0.0.1")  # default to localhost for easy testing
        self.ip_in.pack(pady=10, ipady=8)
        
        tk.Button(self.login, text="join game", font=(THEME["face"], 12, "bold"), bg=THEME["accent"], command=self.connect).pack(pady=10)

    def show_game(self):
        # swap out the login screen for the actual game board
        self.login.destroy()
        self.status_var = tk.StringVar(value="waiting...")
        tk.Label(self.main, textvariable=self.status_var, font=(THEME["face"], 16, "bold"), fg="white", bg=THEME["bg"]).pack(pady=15)
        
        # canvas is where we draw the grid and pieces
        self.canvas = tk.Canvas(self.main, width=COLS * THEME["cell"], height=ROWS * THEME["cell"], bg=THEME["card"], highlightthickness=0)
        self.canvas.pack(padx=20, pady=10)
        self.canvas.bind("<Button-1>", self.on_click)
        
        # "play again" button — hidden until the game ends
        self.footer = tk.Frame(self.main, bg=THEME["bg"])
        tk.Button(self.footer, text="PLAY AGAIN", font=(THEME["face"], 14, "bold"), bg=THEME["accent"], command=lambda: self.send({"type": "RESET"})).pack(pady=10)
        self.draw()

    def connect(self):
        # open TCP socket, transition to game screen, send handshake, start listener thread
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.ip_in.get(), PORT))
            self.show_game()
            self.send({"type": "CONNECT"})  # tell the server we've arrived
            threading.Thread(target=self.listen, daemon=True).start()
        except:
            pass

    def send(self, data):
        # serialize to JSON 
        if self.sock:
            self.sock.sendall((json.dumps(data) + "\n").encode())

    def listen(self):
        # background thread
        # reads from the socket and schedules GUI updates on the main thread
        buf = ""
        while True:
            try:
                raw = self.sock.recv(4096).decode()
                if not raw: break  # server closed connection
                buf += raw

                # split on newline to handle TCP stream fragmentation
                while "\n" in buf:
                    msg_str, buf = buf.split("\n", 1)
                    #safely hands off to the main thread, tkinter is not thread-safe
                    self.root.after(0, self.handle_msg, json.loads(msg_str))
            except:
                break

    def handle_msg(self, msg):
        # called on the main thread 
        if msg["type"] == "WELCOME":
            # server told us our role (R or Y)
            self.role = msg["payload"]
            self.status_var.set(f"you are player {self.role}")
        elif msg["type"] == "UPDATE":
            # new board state from server 
            self.board, self.win_line = msg["board"], msg.get("win_coords") or []
            self.draw()
            
            if msg["status"] == "ongoing":
                self.game_over = False
                self.footer.pack_forget()  # hide play again button during active game
                self.status_var.set("YOUR TURN" if msg["turn"] == self.role else "opponent's turn...")
            else:
                # game ended. show result and play again button
                self.game_over = True
                self.status_var.set(msg["status"].upper())
                self.footer.pack(pady=20)

    def draw(self):
        # redraw every cell on the canvas based on current board state
        self.canvas.delete("all")
        for r in range(ROWS):
            for c in range(COLS):
                x1, y1 = c * THEME["cell"] + THEME["space"], r * THEME["cell"] + THEME["space"]
                x2, y2 = x1 + THEME["cell"] - THEME["space"]*2, y1 + THEME["cell"] - THEME["space"]*2
                
                val = self.board[r][c]
                color = THEME["red"] if val == "R" else THEME["yel"] if val == "Y" else THEME["hole"]
                
                # highlight winning pieces with a white border
                lw = 4 if [r, c] in self.win_line or (r, c) in self.win_line else 0
                self.canvas.create_oval(x1, y1, x2, y2, fill=color, outline="white", width=lw)

    def on_click(self, event):
        # convert x pixel to column index and send move to server
        if not self.game_over and self.role:
            self.send({"type": "MOVE", "col": event.x // THEME["cell"]})

if __name__ == "__main__":
    root = tk.Tk()
    ConnectFourClient(root)
    root.mainloop()