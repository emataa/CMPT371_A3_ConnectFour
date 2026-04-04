"""
client.py - connect four client
cmpt 371 assignment 3

connects to the server over tcp, grabs game updates,
and lets you click to drop pieces using tkinter.

how it talks to the server:
send: "MOVE:<col>"      (e.g., "MOVE:3" to drop in col 3)
recv: "ASSIGN:<colour>" (e.g., "ASSIGN:R" - tells us our color)
      "BOARD:<state>"   (e.g., "BOARD:000...000" - the grid)
      "TURN:<colour>"   (e.g., "TURN:R" - whose turn it is)
      "WIN:<colour>"    (e.g., "WIN:R" - game over, this color won)
      "DRAW"            (board is full, rip)

0 = empty, R = red, Y = yellow
"""

import socket
import threading
import tkinter as tk
from tkinter import messagebox

# ---------------- Configuration ----------------

# net settings
SERVER_PORT = 5050
BUFFER_SIZE = 1024      # max bytes per receive call

# board size
ROWS = 6
COLS = 7

# ---------------- UI Settings ----------------

# ui colors and sizing
CELL_SIZE = 80              # pixels per square
PIECE_PAD = 8               # padding so the circles don't touch the edges
BG_COLOUR = "#1a1a2e"       # dark background
BOARD_COLOUR = "#16213e"    # board panel color
EMPTY_COLOUR = "#0f3460"    # empty hole color
RED_COLOUR = "#e94560"      # player 1 piece
YELLOW_COLOUR = "#f5a623"   # player 2 piece
HOVER_COLOUR = "#ffffff"    # lights up the column your mouse is over

# ---------------- ConnectFourClient Class ----------------
class ConnectFourClient:
    """
    handles the connection and the gui window.
    network stuff runs in the background so the window doesn't freeze up.
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Connect Four")
        self.root.configure(bg=BG_COLOUR)

        # game state - network thread updates this, gui thread reads it
        self.board = [["0"] * COLS for _ in range(ROWS)]  # 6x7 grid
        self.my_colour = None       # "R" or "Y", server tells us later
        self.current_turn = None    # "R" or "Y"
        self.game_over = False

        self.sock = None            # tcp socket, set when we connect

        # draw the window first, then ask for the ip
        self._build_ui()
        self.root.after(100, self._prompt_connection)

    # ---------------- UI ----------------

    def _build_ui(self):
        """builds the actual tkinter stuff"""
        # status text at the top so we know what's going on
        self.status_var = tk.StringVar(value="connecting...")

        tk.Label(
            self.root,
            textvariable=self.status_var,
            font=("Courier", 14, "bold"),
            fg="white",
            bg=BG_COLOUR
        ).pack(pady=10)

        # the canvas where we draw the board and pieces
        self.canvas = tk.Canvas(
            self.root,
            width=COLS * CELL_SIZE,
            height=ROWS * CELL_SIZE,
            bg=BOARD_COLOUR,
            highlightthickness=0
        )
        self.canvas.pack(padx=20, pady=20)

        # catch mouse clicks and hovers
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Motion>", self._on_hover)
        self.canvas.bind("<Leave>", lambda e: self._draw_board())

        self._draw_board()

    def _draw_board(self):
        """wipes the canvas and redraws all the pieces based on self.board"""
        self.canvas.delete("all")

        for r in range(ROWS):
            for c in range(COLS):
                # figure out the coordinates for this circle
                x1 = c * CELL_SIZE + PIECE_PAD
                y1 = r * CELL_SIZE + PIECE_PAD
                x2 = x1 + CELL_SIZE - PIECE_PAD * 2
                y2 = y1 + CELL_SIZE - PIECE_PAD * 2

                # pick the right color
                val = self.board[r][c]
                colour = EMPTY_COLOUR
                if val == "R":
                    colour = RED_COLOUR
                elif val == "Y":
                    colour = YELLOW_COLOUR

                self.canvas.create_oval(x1, y1, x2, y2, fill=colour, outline="")

    # ---------------- Networking ----------------

    def _connect(self, ip):
        """tries to open the socket and starts the listener thread"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((ip, SERVER_PORT))
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        threading.Thread(target=self._receive, daemon=True).start()

    def _send(self, msg):
        try:
            if self.sock:
                self.sock.sendall((msg + "\n").encode())
        except Exception as e:
            print("Send error:", e)

    def _receive(self):
        buffer = ""

        while True:
            try:
                data = self.sock.recv(BUFFER_SIZE).decode()
                if not data:
                    break

                buffer += data

                while "\n" in buffer:
                    msg, buffer = buffer.split("\n", 1)
                    self._handle_message(msg.strip())

            except Exception as e:
                print("Receive error:", e)
                break

    def _end_game(self, message):
        """show popup and close the app (runs on main thread)."""
        def close():
            messagebox.showinfo("Game Over", message)
            self.root.destroy()

        self.root.after(0, close)

    # ---------------- Message Handling ----------------

    def _handle_message(self, msg):
        if msg.startswith("ASSIGN:"):
            self.my_colour = msg.split(":")[1]
            self.status_var.set(f"You are {self.my_colour}")

        elif msg.startswith("BOARD:"):
            state = msg.split(":")[1]
            self._update_board(state)

        elif msg.startswith("TURN:"):
            self.current_turn = msg.split(":")[1]

            if self.current_turn == self.my_colour:
                self.status_var.set("Your turn")
            else:
                self.status_var.set("Opponent's turn")

        elif msg.startswith("WIN:"):
            winner = msg.split(":")[1]
            self.game_over = True

            if winner == self.my_colour:
                self._end_game("You win!")
            else:
                self._end_game("You lose!")

        elif msg == "DRAW":
            self.game_over = True
            self._end_game("Draw!")

    def _update_board(self, state):
        for i, char in enumerate(state):
            r = i // COLS
            c = i % COLS
            self.board[r][c] = char

        self._draw_board()

    # ---------------- Interaction ----------------

    def _on_click(self, event):
        """fires a MOVE message to the server if it's our turn"""
        if self.game_over:
            return

        if self.current_turn != self.my_colour:
            return  # not our turn, ignore the click

        col = event.x // CELL_SIZE
        self._send(f"MOVE:{col}")

    def _on_hover(self, event):
        """highlights the column so the player knows where they're dropping"""
        if self.game_over or self.current_turn != self.my_colour:
            return

        col = event.x // CELL_SIZE
        self._draw_board()  # clean the board first

        # draw a thin box over the hovered column
        x1 = col * CELL_SIZE
        x2 = x1 + CELL_SIZE
        self.canvas.create_rectangle(
            x1, 0, x2, ROWS * CELL_SIZE,
            outline=HOVER_COLOUR,
            width=2
        )

    def _on_leave(self, _event):
        """mouse left the board, get rid of the highlight"""
        self._draw_board()

    # ---------------- Connect Prompt ----------------

    def _prompt_connection(self):
        """a little pop-up to ask where the server is running"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Connect")
        dialog.resizable(False, False)
        dialog.grab_set()  # lock the main window until they answer

        tk.Label(dialog, text="Server IP:").pack(pady=5)

        tk.Label(dialog, text="server ip address:", font=("Courier", 12), padx=20, pady=10).pack()
        ip_entry = tk.Entry(dialog, font=("Courier", 12), width=20)
        ip_entry.insert(0, "127.0.0.1")  # defaults to localhost for easy testing
        ip_entry.pack(padx=20)
        ip_entry.focus()

        def connect():
            ip = ip_entry.get()
            dialog.destroy()
            self._connect(ip)
            self.status_var.set("Connected. Waiting...")

        tk.Button(dialog, text="Connect", command=connect).pack(pady=10)

# ---------------- MAIN ----------------

if __name__ == "__main__":
    root = tk.Tk()
    app = ConnectFourClient(root)
    root.mainloop()