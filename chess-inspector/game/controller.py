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

    # Standard material values, used only for the "weighted" calculation
    # mode below - not used by "uniform" mode at all.
    _PIECE_VALUES = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
        chess.KING: 0,  # king mobility isn't material pressure, weight it out
    }

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
        # Point the shared game's current position at the start of *this*
        # game. Without this, self.fen/self.last_fen are left untouched by
        # a PGN upload, so the index page keeps rendering whatever fen was
        # previously persisted (e.g. from the last manual move or a prior
        # PGN) instead of the game the user just selected.
        self.last_fen = fens[0]
        self.fen = fens[0]
        return fens

    def get_move_probabilities(self, calc="uniform"):
        """
        For each piece currently on the board, compute a probability over
        that piece's own legal destination squares. Returns a dict split
        by color first:
        { "white": {origin: {dest: {"probability": p, "capture": bool}}},
        "black": {...} }

        calc controls how probability mass is distributed:
        - "uniform" (default): 1 / that piece's legal-move count, so every
        piece's own moves sum to 1 regardless of what kind of piece it is.
        - "weighted": piece_value / legal-move count, so a queen's moves
        collectively carry more weight in an aggregate heatmap than a
        pawn's - this does NOT sum to 1 per piece by design, since the
        point is to let higher-value pieces dominate the aggregate.
        """
        if self.fen:
            self.board = chess.Board(self.fen)
        else:
            self.board = chess.Board()

        board = self.board
        result = {"white": {}, "black": {}}

        # "optimal" needs to know, for each candidate destination square,
        # whether the opponent threatens it - that's exactly what
        # Coverage.cover()'s is_threatened_by list tracks per square.
        # Static data about the board as it currently sits, so it's
        # computed once up front rather than per color in the loop below.
        cover = json.loads(self.get_coverage()) if calc == "optimal" else None

        for color in (chess.WHITE, chess.BLACK):
            board.turn = color
            color_key = "white" if color == chess.WHITE else "black"
            by_origin = {}
            for move in board.legal_moves:
                by_origin.setdefault(move.from_square, []).append(move)

            for origin, moves in by_origin.items():
                square_name = chess.square_name(origin)

                if calc == "optimal":
                    moves = [m for m in moves if not self._dest_is_threatened(cover, board, m)]
                    n = len(moves)
                    if n == 0:
                        # Every destination for this piece is threatened -
                        # leave the square out of the result entirely
                        # rather than dividing by zero, so nothing gets
                        # colored for it.
                        continue
                    per_move = 1 / n
                elif calc == "weighted":
                    n = len(moves)
                    piece = board.piece_at(origin)
                    weight = self._PIECE_VALUES.get(piece.piece_type, 1) if piece else 1
                    per_move = weight / n
                elif calc == "by_moves":
                    n = len(moves)
                    per_move = n / 64
                else:
                    n = len(moves)
                    per_move = 1 / n

                result[color_key][square_name] = {
                    chess.square_name(move.to_square): {
                        "probability": round(per_move, 4),
                        "capture": board.is_capture(move),
                    }
                    for move in moves
                }

        return json.dumps(result, sort_keys=True)

    def _dest_is_threatened(self, cover, board, move):
        """
        True if the move's destination square would be under threat from
        the opponent, per Coverage's cover() data.

        Coverage only populates is_threatened_by/is_protected_by for
        squares that currently hold a piece (see chess_coverage's own
        cover() - both fields are set inside an `if piece:` guard), so a
        non-capture move (landing on an empty square) never has an
        is_threatened_by entry to check, regardless of whether the
        square is actually attacked. The field that IS populated for
        empty squares is "<color>_can_capture_here" - the origin squares
        of <color>'s pieces that could capture something placed there.

        A capture is different: the destination is currently occupied by
        the piece being captured, and its is_protected_by list names the
        opponent's OTHER pieces defending it - i.e. exactly who would be
        left to recapture once that piece is taken.

        En passant is a capture (board.is_capture is True) but its
        destination square is empty like a normal move - the captured
        pawn sits on a different square - so it's checked the same way
        as a non-capture.
        """
        dest = chess.square_name(move.to_square)
        dest_cover = cover.get(dest, {})
        mover_color = board.piece_at(move.from_square).color
        opponent = 'black' if mover_color == chess.WHITE else 'white'

        if board.is_capture(move) and not board.is_en_passant(move):
            return len(dest_cover.get("is_protected_by", [])) > 0
        return len(dest_cover.get(f"{opponent}_can_capture_here", [])) > 0
