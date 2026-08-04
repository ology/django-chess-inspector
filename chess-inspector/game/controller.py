import chess
import chess.pgn
from chess_coverage import Coverage
import io
import json
import logging
import re

class Controller:
    current_user_id = 0
    fen = ''
    last_fen = ''
    pgn_file = ''
    pgn_date = ''
    pgn_site = ''
    pgn_white = ''
    pgn_black = ''
    board = None
    en_passant = True
    logger = logging.getLogger('debug')

    def __init__(self):
        pass

    def save_state(self, account_id=None):
        """
        Persists the shared game's current position to a single row
        (id=1) in the Game table - there's only ever one shared game in
        this app, so this updates that one row rather than accumulating
        a new row per move. account_id is stored for informational
        purposes only (who moved most recently); it doesn't scope which
        game this is, since the game itself is shared, not per-account.
        """
        try:
            from .models import Game
            saved, _ = Game.objects.get_or_create(
                id=1, defaults={'account_id': account_id or 0}
            )
            if account_id is not None:
                saved.account_id = account_id
            saved.fen = self.fen
            saved.last_fen = self.last_fen
            saved.save()
        except Exception as e:
            self.logger.error(f"Could not persist game state: {e}")

    def load_state(self):
        """
        Restores the shared game's last-saved position. Broadly
        try/except'd on purpose: this gets called from GameConfig.ready()
        at process startup, which on a brand new install runs BEFORE
        `manage.py migrate` has created the table at all - this must not
        raise in that case, just leave fen/last_fen at their defaults.
        """
        try:
            from .models import Game
            saved = Game.objects.filter(id=1).first()
            if saved:
                self.fen = saved.fen
                self.last_fen = saved.last_fen
        except Exception as e:
            self.logger.error(f"Could not load persisted game state: {e}")

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

    def add_en_passant(self, cover, p, n, m, color_name):
        key = "is_threatened_by"
        if not key in cover[p]:
            cover[p][key] = []
        cover[p][key].append(n)
        key = f"{color_name}_can_move_here"
        if not key in cover[m]:
            cover[m][key] = []
        cover[m][key].append(p)
        cover[n]["moves"].append(m)
        return cover

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
                    # self.logger.debug(f"P at {file}{rank} has neighbor: {neighbor} at {n}")
                    cover = self.add_en_passant(cover, p, n, m, 'black')
        if re.search(r"[a-h]", neighbors[1]):
            n = f"{neighbors[1]}{rank}"
            neighbor = c.get_piece(self.board, n)
            if neighbor and (not neighbor.color):
                m = f"{file}{rank - 1}"
                to = c.get_piece(self.board, m)
                if not to:
                    # self.logger.debug(f"P at {p} has neighbor: {neighbor} at {n}")
                    cover = self.add_en_passant(cover, p, n, m, 'black')
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
                    # self.logger.debug(f"p at {file}{rank} has neighbor: {neighbor} at {n}")
                    cover = self.add_en_passant(cover, p, n, m, 'white')
        if re.search(r"[a-h]", neighbors[1]):
            n = f"{neighbors[1]}{rank}"
            neighbor = c.get_piece(self.board, n)
            if neighbor and (neighbor.color):
                m = f"{file}{rank + 1}"
                to = c.get_piece(self.board, m)
                if not to:
                    # self.logger.debug(f"p at {file}{rank} has neighbor: {neighbor} at {n}")
                    cover = self.add_en_passant(cover, p, n, m, 'white')
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

    def pgn(self):
        fens = []
        game_text = ''
        for line in self.pgn_file:
            game_text = game_text + line.decode()
        pgn = io.StringIO(game_text)
        game = chess.pgn.read_game(pgn)
        self.pgn_date = game.headers['Date']
        self.pgn_site = game.headers['Site']
        self.pgn_white = game.headers['White']
        self.pgn_black = game.headers['Black']
        board = game.board()
        fens.append(board.fen())
        for move in game.mainline_moves():
            board.push(move)
            fens.append(board.fen())
        # self.logger.debug(f"FENS: {fens}")
        return fens
    