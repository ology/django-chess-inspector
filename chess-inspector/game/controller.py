import chess
from chess_coverage import Coverage
import json
import logging
import re

class Controller:
    current_user_id = 0
    fen = ''
    board = None
    en_passant = True
    logger = logging.getLogger('debug')

    def __init__(self):
        pass

    def get_coverage(self):
        if self.fen:
            self.board = chess.Board(self.fen)
        else:
            self.board = chess.Board()
        c = Coverage(self.board)
        cover = c.cover()
        if self.en_passant:
            cover = self.hunt_en_passant(cover)
        return json.dumps(cover, sort_keys=True)

    def hunt_en_passant(self, cover):
        c = Coverage(self.board)
        whites = [ f"{f}4" for f in list('abcdefgh') ]
        blacks = [ f"{f}5" for f in list('abcdefgh') ]
        for p in whites:
            piece = c.get_piece(self.board, p)
            if piece and (piece.symbol() == 'P'):
                file = p[0]
                neighbors = [chr(ord(file) - 1), chr(ord(file) + 1)]
                if re.search(r"[a-h]", neighbors[0]):
                    n = f"{neighbors[0]}4"
                    neighbor = c.get_piece(self.board, n)
                    if neighbor:
                        self.logger.error(f"P at {p} has neighbor: {neighbor} at {n}")
                if re.search(r"[a-h]", neighbors[1]):
                    n = f"{neighbors[1]}4"
                    neighbor = c.get_piece(self.board, n)
                    if neighbor:
                        self.logger.error(f"P at {p} has neighbor: {neighbor} at {n}")
        # for p in blacks:
        #     self.logger.error(p)
        return cover
