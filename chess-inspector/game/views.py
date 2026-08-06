import chess
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render, reverse
import json

from .controller import Controller

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
def index(request):
    is_cover = False
    play_n = 0
    if request.method == "POST":
        posted_fen = request.POST.get('fen')
        if not _valid_fen(posted_fen):
            messages.error(request, "That position couldn't be read - ignoring it")
            return redirect("game:index")
        ctrl.last_fen = request.POST.get('last_fen')
        last_fen = ctrl.last_fen
        ctrl.fen = posted_fen
        fen = ctrl.fen
        ctrl.en_passant = _to_bool(request.POST.get('en_passant'), default=ctrl.en_passant)
        is_cover = request.POST.get('is_cover')
        play_n = request.POST.get('play_n') or 0
        ctrl.save_state(account_id=request.user.id)
    else:
        ctrl.load_state()
        last_fen = request.GET.get('last_fen') or ctrl.last_fen or INIT_FEN
        fen = request.GET.get('fen') or ctrl.fen or INIT_FEN
        is_cover = request.GET.get('is_cover')
        play_n = request.GET.get('play_n') or 0
        ctrl.last_fen = last_fen
        ctrl.fen = fen
    coverage = ctrl.get_coverage()
    coverage = json.dumps(coverage)
    context = {
        "last_fen": last_fen,
        "fen": fen,
        "coverage": coverage,
        "is_cover": is_cover,
        "play_n": play_n,
        "pgn_file": ctrl.pgn_file,
        "pgn_date": ctrl.pgn_date,
        "pgn_site": ctrl.pgn_site,
        "pgn_white": ctrl.pgn_white,
        "pgn_black": ctrl.pgn_black,
        "init_fen": INIT_FEN,
    }
    return render(request, "game/index.html", context)

@login_required
def pgn(request):
    if request.method == "POST":
        uploaded = request.FILES.get('pgn')
        if not uploaded:
            messages.error(request, "No PGN file was selected")
            return redirect("game:index")
        ctrl.pgn_file = uploaded
        fens = ctrl.pgn()
        ctrl.save_state(account_id=request.user.id)
        response = HttpResponseRedirect(reverse('game:index'))
        response.set_cookie("fens", json.dumps(fens))
        return response
    return redirect("game:index")

@login_required
def clear_pgn(request):
    if request.method == "POST":
        ctrl.fen = request.POST.get('fen')
    ctrl.pgn_file = ""
    return redirect("game:index")

@login_required
def fen(request):
    if request.method == "POST":
        candidate = request.POST.get('show_fen')
        if not _valid_fen(candidate):
            messages.error(request, "That FEN doesn't look valid")
            return redirect("game:index")
        ctrl.fen = candidate
        fens = [ctrl.fen]
        url = reverse('game:index')
        url += f"?last_fen={ctrl.fen}"
        response = HttpResponseRedirect(url)
        response.set_cookie("fens", json.dumps(fens))
    else:
        response = redirect("game:index")
    ctrl.pgn_file = ""
    return response

@login_required
def probability(request):
    ctrl.load_state()
    fen = request.GET.get('fen') or ctrl.fen or INIT_FEN
    calc = request.GET.get('calc') or 'uniform'
    if calc not in ('uniform', 'weighted'):
        calc = 'uniform'
    ctrl.fen = fen
    move_probs = ctrl.get_move_probabilities(calc=calc)
    context = {
        "fen": fen,
        "move_probs": move_probs,
        "calc": calc,
        "init_fen": INIT_FEN,
    }
    return render(request, "game/probability.html", context)
