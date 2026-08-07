import chess
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
import json

from .controller import Controller
from .models import Game

ctrl = Controller()

INIT_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"

def _valid_fen(fen_str):
    try:
        chess.Board(fen_str)
        return True
    except ValueError:
        return False

def _to_bool(value, default):
    """
    Coerce a value from request.POST.get(...) into a real bool.
    - None (the field wasn't submitted at all) keeps the previous state,
      rather than silently flipping it to False.
    - Recognized truthy tokens (case-insensitive) become True.
    - Anything else - including the literal string "false" - becomes
      False. Plain truthiness on a string would get this backwards,
      since "false" is a non-empty string and therefore truthy in Python.
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ('true', '1', 'on', 'yes')

def _most_recent_or_new_game_id(account_id=None):
    """
    Finds the most recently updated game in the shared lobby, or creates
    a brand new one if none exist yet. Used whenever a route needs
    somewhere sensible to land without a specific game_id in hand (the
    bare index route, or recovering from a stale/bad game_id in a URL).
    """
    most_recent = Game.objects.order_by('-updated').first()
    if most_recent:
        return most_recent.id
    return Game.objects.create(account_id=account_id or 0).id

def _game_exists(game_id):
    return Game.objects.filter(id=game_id).exists()

def login_page(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        if not User.objects.filter(username=username).exists():
            messages.error(request, "Invalid login")
            return redirect('/accounts/login/')
        user = authenticate(username=username, password=password)
        if user is None:
            messages.error(request, "Invalid login")
            return redirect('/accounts/login/')
        login(request, user)
        request.session['user_id'] = user.id
        request.session.save()
        return redirect("game:index")
    return render(request, 'login.html')

@login_required
def index(request, game_id=None):
    # No game specified (bare "/") - land on the most recently active
    # game in the shared lobby, or start a fresh one if the lobby is
    # empty. Redirecting (rather than rendering here directly) means the
    # address bar - and therefore the per-game WebSocket room this page
    # connects to - always reflects exactly which game is being viewed,
    # so a bookmarked or shared link to a specific game is meaningful.
    if game_id is None:
        return redirect("game:index", game_id=_most_recent_or_new_game_id(account_id=request.user.id))

    if not _game_exists(game_id):
        messages.error(request, "That game doesn't exist anymore - showing the most recent one instead")
        return redirect("game:index", game_id=_most_recent_or_new_game_id(account_id=request.user.id))

    is_cover = False
    play_n = 0
    # Resync from the DB before anything else, on every request - not
    # just GET. This makes pgn_filename/pgn_date/pgn_site/pgn_white/
    # pgn_black/fens (and fen/last_fen) consistent no matter which worker
    # process ends up handling this request versus whichever one handled
    # the upload or the last move - and, now that ctrl serves whichever
    # game_id each request asks for, it's also what loads the RIGHT
    # game's state rather than whatever the previous request left behind.
    ctrl.load_state(game_id)
    if request.method == "POST":
        posted_fen = request.POST.get('fen')
        if not _valid_fen(posted_fen):
            messages.error(request, "That position couldn't be read - ignoring it")
            return redirect("game:index", game_id=game_id)
        ctrl.last_fen = request.POST.get('last_fen')
        last_fen = ctrl.last_fen
        ctrl.fen = posted_fen
        fen = ctrl.fen
        ctrl.en_passant = _to_bool(request.POST.get('en_passant'), default=ctrl.en_passant)
        is_cover = request.POST.get('is_cover')
        play_n = request.POST.get('play_n') or 0
        ctrl.save_state(game_id=game_id, account_id=request.user.id)
    else:
        last_fen = request.GET.get('last_fen') or ctrl.last_fen or INIT_FEN
        fen = request.GET.get('fen') or ctrl.fen or INIT_FEN
        is_cover = request.GET.get('is_cover')
        play_n = request.GET.get('play_n') or 0
        ctrl.last_fen = last_fen
        ctrl.fen = fen
    coverage = ctrl.get_coverage()
    coverage = json.dumps(coverage)
    context = {
        "game_id": game_id,
        # Powers the game-switcher dropdown - every game in the shared
        # lobby, most recently active first.
        "games": Game.objects.order_by('-updated'),
        "last_fen": last_fen,
        "fen": fen,
        "coverage": coverage,
        "is_cover": is_cover,
        "play_n": play_n,
        # Was ctrl.pgn_file (the raw UploadedFile) - that's per-process,
        # never persisted, and not meaningfully renderable across workers.
        # pgn_filename is the persisted stand-in and renders identically
        # for the template's truthiness checks and display.
        "pgn_file": ctrl.pgn_filename,
        "pgn_date": ctrl.pgn_date,
        "pgn_site": ctrl.pgn_site,
        "pgn_white": ctrl.pgn_white,
        "pgn_black": ctrl.pgn_black,
        # Replaces the old "fens" cookie - fed straight into the page the
        # same way move_probs already is in probability.html, so the play
        # forward/backward/end controls no longer depend on parsing a
        # cookie value through several layers of escaping.
        "fens": json.dumps(ctrl.fens),
        "init_fen": INIT_FEN,
    }
    return render(request, "game/index.html", context)

@login_required
def new_game(request):
    if request.method != "POST":
        return redirect("game:index")
    game = Game.objects.create(account_id=request.user.id)
    messages.success(request, f"Started new game #{game.id}")
    return redirect("game:index", game_id=game.id)

@login_required
def delete_game(request, game_id):
    if request.method != "POST":
        return redirect("game:index", game_id=game_id)
    if not _game_exists(game_id):
        messages.error(request, "That game doesn't exist anymore")
        return redirect("game:index")
    Game.objects.filter(id=game_id).delete()
    messages.success(request, f"Deleted game #{game_id}")
    # Land somewhere sensible now that this game is gone - the most
    # recently active REMAINING game, or a fresh one if that was the
    # last game in the lobby. This runs after the delete, so
    # _most_recent_or_new_game_id() can't just hand back the game we
    # were on a moment ago.
    return redirect("game:index", game_id=_most_recent_or_new_game_id(account_id=request.user.id))

@login_required
def pgn(request, game_id):
    if not _game_exists(game_id):
        messages.error(request, "That game doesn't exist anymore")
        return redirect("game:index")
    if request.method == "POST":
        uploaded = request.FILES.get('pgn')
        if not uploaded:
            messages.error(request, "No PGN file was selected")
            return redirect("game:index", game_id=game_id)
        ctrl.load_state(game_id)
        ctrl.pgn_file = uploaded
        ctrl.pgn()
        ctrl.save_state(game_id=game_id, account_id=request.user.id)
        return redirect("game:index", game_id=game_id)
    return redirect("game:index", game_id=game_id)

@login_required
def clear_pgn(request, game_id):
    if not _game_exists(game_id):
        messages.error(request, "That game doesn't exist anymore")
        return redirect("game:index")
    ctrl.load_state(game_id)
    if request.method == "POST":
        ctrl.fen = request.POST.get('fen')
    ctrl.pgn_file = ""
    ctrl.pgn_filename = ""
    ctrl.pgn_date = ""
    ctrl.pgn_site = ""
    ctrl.pgn_white = ""
    ctrl.pgn_black = ""
    ctrl.fens = []
    ctrl.save_state(game_id=game_id, account_id=request.user.id)
    return redirect("game:index", game_id=game_id)

@login_required
def fen(request, game_id):
    if not _game_exists(game_id):
        messages.error(request, "That game doesn't exist anymore")
        return redirect("game:index")
    ctrl.load_state(game_id)
    if request.method == "POST":
        candidate = request.POST.get('show_fen')
        if not _valid_fen(candidate):
            messages.error(request, "That FEN doesn't look valid")
            return redirect("game:index", game_id=game_id)
        # This view previously only ever set ctrl.fen in memory and built
        # a "fens" cookie by hand - it never actually called save_state(),
        # so an uploaded FEN was never really persisted (it just happened
        # to render once via the cookie/last_fen query param combo before
        # silently reverting on the next real load). Bringing it in line
        # with the rest of the app: persist it properly, and treat a
        # manually-entered FEN as clearing any in-progress PGN playback,
        # same as the explicit "Clear PGN" action does, since a hand-typed
        # position isn't part of that PGN's move sequence anymore.
        ctrl.fen = candidate
        ctrl.last_fen = candidate
        ctrl.pgn_file = ""
        ctrl.pgn_filename = ""
        ctrl.pgn_date = ""
        ctrl.pgn_site = ""
        ctrl.pgn_white = ""
        ctrl.pgn_black = ""
        ctrl.fens = []
        ctrl.save_state(game_id=game_id, account_id=request.user.id)
    return redirect("game:index", game_id=game_id)

@login_required
def probability(request, game_id):
    if not _game_exists(game_id):
        messages.error(request, "That game doesn't exist anymore")
        return redirect("game:index")
    ctrl.load_state(game_id)
    fen = request.GET.get('fen') or ctrl.fen or INIT_FEN
    calc = request.GET.get('calc') or 'uniform'
    if calc not in ('uniform', 'weighted', 'by_moves', 'optimal'):
        calc = 'uniform'
    ctrl.fen = fen
    move_probs = ctrl.get_move_probabilities(calc=calc)
    context = {
        "game_id": game_id,
        "fen": fen,
        "move_probs": move_probs,
        "calc": calc,
        "init_fen": INIT_FEN,
    }
    return render(request, "game/probability.html", context)
