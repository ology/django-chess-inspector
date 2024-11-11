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
        rank = 4
        p = f"{file}{rank}"
        if re.search(r"[a-h]", neighbors[0]):
            n = f"{neighbors[0]}{rank}"
            neighbor = c.get_piece(self.board, n)
            if neighbor and (not neighbor.color):
                m = f"{file}{rank - 1}"
                to = c.get_piece(self.board, m)
                if not to:
                    self.logger.error(f"P at {file}{rank} has neighbor: {neighbor} at {n}")
                    if not "is_threatened_by" in cover[p]:
                        cover[p]["is_threatened_by"] = []
                    cover[p]["is_threatened_by"].append(n)
                    if not "black_can_move_here" in cover[m]:
                        cover[m]["black_can_move_here"] = []
                    cover[p]["is_threatened_by"].append(n)
                    cover[m]["black_can_move_here"].append(p)
        if re.search(r"[a-h]", neighbors[1]):
            n = f"{neighbors[1]}{rank}"
            neighbor = c.get_piece(self.board, n)
            if neighbor and (not neighbor.color):
                m = f"{file}{rank - 1}"
                to = c.get_piece(self.board, m)
                if not to:
                    self.logger.error(f"P at {p} has neighbor: {neighbor} at {n}")
                    if not "is_threatened_by" in cover[p]:
                        cover[p]["is_threatened_by"] = []
                    cover[p]["is_threatened_by"].append(n)
                    if not "black_can_move_here" in cover[m]:
                        cover[m]["black_can_move_here"] = []
                    cover[p]["is_threatened_by"].append(n)
                    cover[m]["black_can_move_here"].append(p)
        return cover

    def black_neighborhood(self, file, neighbors, c, cover):
        rank = 5
        p = f"{file}{rank}"
        if re.search(r"[a-h]", neighbors[0]):
            n = f"{neighbors[0]}{rank}"
            neighbor = c.get_piece(self.board, n)
            if neighbor and (neighbor.color):
                m = f"{file}{rank + 1}"
                to = c.get_piece(self.board, m)
                if not to:
                    self.logger.error(f"p at {file}{rank} has neighbor: {neighbor} at {n}")
                    if not "is_threatened_by" in cover[p]:
                        cover[p]["is_threatened_by"] = []
                    cover[p]["is_threatened_by"].append(n)
                    if not "white_can_move_here" in cover[m]:
                        cover[m]["white_can_move_here"] = []
                    cover[m]["white_can_move_here"].append(p)
        if re.search(r"[a-h]", neighbors[1]):
            n = f"{neighbors[1]}{rank}"
            neighbor = c.get_piece(self.board, n)
            if neighbor and (neighbor.color):
                m = f"{file}{rank + 1}"
                to = c.get_piece(self.board, m)
                if not to:
                    self.logger.error(f"p at {file}{rank} has neighbor: {neighbor} at {n}")
                    if not "is_threatened_by" in cover[p]:
                        cover[p]["is_threatened_by"] = []
                    cover[p]["is_threatened_by"].append(n)
                    if not "white_can_move_here" in cover[m]:
                        cover[m]["white_can_move_here"] = []
                    cover[p]["is_threatened_by"].append(n)
                    cover[m]["white_can_move_here"].append(p)
        return cover

    def neighborhood(self, symbol, list, cover, c):
        for p in list:
            piece = c.get_piece(self.board, p)
            if piece and (piece.symbol() == symbol):
                file = p[0]
                neighbors = [chr(ord(file) - 1), chr(ord(file) + 1)]
                if symbol == 'P':
                    cover = self.white_neighborhood(file, neighbors, c, cover)
                else:
                    cover = self.black_neighborhood(file, neighbors, c, cover)
        return cover

    def hunt_en_passant(self, cover):
        c = Coverage(self.board)
        whites = [ f"{f}4" for f in list('abcdefgh') ]
        cover = self.neighborhood('P', whites, cover, c)
        blacks = [ f"{f}5" for f in list('abcdefgh') ]
        cover = self.neighborhood('p', blacks, cover, c)
        return cover
