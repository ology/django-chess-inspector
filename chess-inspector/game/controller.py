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

    def white_neighborhood(self, file, neighbors, c, cover):
        if re.search(r"[a-h]", neighbors[0]):
            n = f"{neighbors[0]}4"
            neighbor = c.get_piece(self.board, n)
            if neighbor and (not neighbor.color):
                m = f"{file}3"
                to = c.get_piece(self.board, m)
                if not to:
                    self.logger.error(f"P at {file}4 has neighbor: {neighbor} at {n}")
        if re.search(r"[a-h]", neighbors[1]):
            n = f"{neighbors[1]}4"
            neighbor = c.get_piece(self.board, n)
            if neighbor and (not neighbor.color):
                m = f"{file}3"
                to = c.get_piece(self.board, m)
                if not to:
                    self.logger.error(f"P at {file}4 has neighbor: {neighbor} at {n}")
        return cover

    def black_neighborhood(self, file, neighbors, c, cover):
        if re.search(r"[a-h]", neighbors[0]):
            n = f"{neighbors[0]}5"
            neighbor = c.get_piece(self.board, n)
            if neighbor and (neighbor.color):
                m = f"{file}6"
                to = c.get_piece(self.board, m)
                if not to:
                    self.logger.error(f"p at {file}5 has neighbor: {neighbor} at {n}")
        if re.search(r"[a-h]", neighbors[1]):
            n = f"{neighbors[1]}5"
            neighbor = c.get_piece(self.board, n)
            if neighbor and (neighbor.color):
                m = f"{file}6"
                to = c.get_piece(self.board, m)
                if not to:
                    self.logger.error(f"p at {file}5 has neighbor: {neighbor} at {n}")
        return cover

    def hunt_en_passant(self, cover):
        c = Coverage(self.board)
        whites = [ f"{f}4" for f in list('abcdefgh') ]
        blacks = [ f"{f}5" for f in list('abcdefgh') ]
        for p in whites:
            piece = c.get_piece(self.board, p)
            if piece and (piece.symbol() == 'P'):
                file = p[0]
                neighbors = [chr(ord(file) - 1), chr(ord(file) + 1)]
                cover = self.white_neighborhood(file, neighbors, c, cover)
        for p in blacks:
            piece = c.get_piece(self.board, p)
            if piece and (piece.symbol() == 'p'):
                file = p[0]
                neighbors = [chr(ord(file) - 1), chr(ord(file) + 1)]
                cover = self.black_neighborhood(file, neighbors, c, cover)
        return cover
