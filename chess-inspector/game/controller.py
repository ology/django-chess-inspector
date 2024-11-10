import chess
from chess_coverage import Coverage
import json
import logging

class Controller:
    current_user_id = 0
    fen = ''
    board = None
    logger = logging.getLogger('debug')

    def __init__(self):
        pass

    def get_coverage(self):
        # self.logger.error(f"CFEN: {self.fen}")
        if self.fen:
            self.board = chess.Board(self.fen)
        else:
            self.board = chess.Board()
        # self.board.push_san("e4")
        # self.board.push_san("d5")
        c = Coverage(self.board)
        cover = c.cover()
        return json.dumps(cover, indent=2, sort_keys=True)
