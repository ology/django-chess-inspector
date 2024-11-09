import chess
import json
from chess_coverage import Coverage

class Controller:
    current_user_id = 0
    board = chess.Board()

    def __init__(self):
        pass

    def get_coverage(self):
        self.board.push_san("e4")
        self.board.push_san("d5")
        c = Coverage(self.board)
        cover = c.cover()
        return json.dumps(cover, indent=2, sort_keys=True)
