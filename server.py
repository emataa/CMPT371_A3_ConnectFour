"""
server.py - connect four client
cmpt 371 assignment 3

Hosts a Connect Four game over TCP. Accepts 2 clients, assigns colors,
receives moves, updates the board, checks for wins or draws,
and broadcasts game state to all connected clients.

Protocol with clients:
Server sends:
    "ASSIGN:<colour>"  -> tells the client their color (R or Y)
    "BOARD:<state>"    -> sends the current board as a flattened string
    "TURN:<colour>"    -> whose turn it is
    "WIN:<colour>"     -> announces a winning color
    "DRAW"             -> board is full, game ends

Clients send:
    "MOVE:<col>"       -> drop a piece in the specified column (0-indexed)

Board representation:
0 = empty, R = red, Y = yellow
Board is 6 rows × 7 columns
"""

import socket
import threading

# ---------------- Configuration ----------------

HOST = "0.0.0.0"  # Listen on all network interfaces
PORT = 5050       # Port number for the server

ROWS = 6          # Connect Four standard board dimensions
COLS = 7

# ---------------- Server Class ----------------

class ConnectFourServer:
    def __init__(self):
        self.board = [["0"] * COLS for _ in range(ROWS)] # Empty board
        self.clients = []               # [(conn, colour)]
        self.current_turn = "R"         # Red goes first
        self.lock = threading.Lock()    # Thread-safe move handling
        self.game_over = False          # Game Over state
        self.server_socket = None       # Will hold listening socket

    # ---------------- Server Setup ----------------

    def start(self):
        # Create TCP server socket
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((HOST, PORT))
        server.listen(2)

        print(f"Server listening on {HOST}:{PORT}")

        # accept exactly 2 players
        while len(self.clients) < 2:
            conn, addr = server.accept()
            colour = "R" if len(self.clients) == 0 else "Y"
            self.clients.append((conn, colour))
            print(f"Player {colour} connected from {addr}")

            conn.sendall(f"ASSIGN:{colour}\n".encode())

            threading.Thread(
                target=self.handle_client,
                args=(conn, colour),
                daemon=True
            ).start()

        print("Both players connected. Starting game.")

        # send initial state
        self.send_board()
        self.broadcast(f"TURN:{self.current_turn}")

        # wait here until game ends
        while not self.game_over:
            threading.Event().wait(1)  # sleep 1 second, allow threads to run

        # shutdown after game over
        self.shutdown_server()

    # ---------------- Interaction ----------------

    def handle_client(self, conn, colour):
        """
        Handle messages from a client.
        Messages may arrive in chunks, so we buffer until newline.
        """
        buffer = ""

        try:
            while True:
                data = conn.recv(1024).decode()
                if not data:
                    break

                buffer += data

                # process full messages
                while "\n" in buffer:
                    msg, buffer = buffer.split("\n", 1)
                    self.process_message(conn, colour, msg.strip())

        except:
            pass
        finally:
            conn.close()

    def process_message(self, conn, colour, msg):
        """
        Interpret a message from the client.
        Currently only handles MOVE messages.
        """

        if msg.startswith("MOVE:"):
            try:
                col = int(msg.split(":")[1])
                self.handle_move(colour, col)
            except:
                pass

    # ---------------- Game Logic ----------------

    def handle_move(self, colour, col):
        """
        Place a piece in the specified column if valid.
        Update the board, check for win/draw, and broadcast updates.
        """
        with self.lock:
            if self.game_over:
                return

            if colour != self.current_turn:
                return

            if not (0 <= col < COLS):
                return

            row = self.get_open_row(col)
            if row is None:
                return  # column full

            self.board[row][col] = colour
            print(f"{colour} placed at column {col}")

            # check win
            if self.check_win(row, col, colour):
                self.send_board()
                self.broadcast(f"WIN:{colour}")
                self.game_over = True
                return

            # check draw
            if self.is_draw():
                self.send_board()
                self.broadcast("DRAW")
                self.game_over = True
                return

            # switch turn
            self.current_turn = "Y" if colour == "R" else "R"

            # Send updated board and turn
            self.send_board()
            self.broadcast(f"TURN:{self.current_turn}")

    def get_open_row(self, col):
        """Return the first empty row in a column, starting from the bottom."""
        for r in range(ROWS - 1, -1, -1):
            if self.board[r][col] == "0":
                return r
        return None

    def is_draw(self):
        """Return True if the board is full (no empty spaces in top row)."""
        return all(self.board[0][c] != "0" for c in range(COLS))

    def check_win(self, row, col, colour):
        """
        Check if placing a piece at (row, col) causes a win.
        Looks in 4 directions: vertical, horizontal, two diagonals.
        """
        directions = [(1,0), (0,1), (1,1), (1,-1)]

        for dx, dy in directions:
            count = 1

            count += self.count_dir(row, col, dx, dy, colour)
            count += self.count_dir(row, col, -dx, -dy, colour)

            if count >= 4:
                return True

        return False

    def count_dir(self, row, col, dx, dy, colour):
        """Count consecutive pieces of the same color in a given direction."""
        r, c = row + dy, col + dx
        count = 0

        while 0 <= r < ROWS and 0 <= c < COLS:
            if self.board[r][c] != colour:
                break
            count += 1
            r += dy
            c += dx

        return count

    # ---------------- Board Communication ----------------

    def board_string(self):
        """Flatten the 2D board into a single string for sending to clients."""
        return "".join(cell for row in self.board for cell in row)

    def send_board(self):
        """Broadcast the current board to all clients."""
        self.broadcast(f"BOARD:{self.board_string()}")

    def broadcast(self, message):
        """Send a message to all connected clients."""
        for conn, _ in self.clients:
            try:
                conn.sendall((message + "\n").encode())
            except:
                pass

    # ---------------- Shutdown ----------------

    def shutdown_server(self):
        """Close all client connections and the server socket."""
        print("Shutting down server...")
        self.game_over = True
        for conn, _ in self.clients:
            try:
                conn.close()
            except:
                pass
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        print("Server closed.")


# ---------------- Main ----------------

if __name__ == "__main__":
    ConnectFourServer().start()
